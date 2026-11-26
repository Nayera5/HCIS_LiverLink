from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .audit import audit
from .models import AuditLog, User
from .permissions import HasCapability
from .serializers import (
    AuditLogFilterSerializer, AuditLogSerializer, ChangePasswordSerializer, LogoutSerializer, MeSerializer, MeUpdateSerializer,
    PasswordResetConfirmSerializer, PasswordResetRequestSerializer, StaffAccountCreateSerializer,
    StaffAccountUpdateSerializer, UserDetailSerializer, UserListSerializer,
)
from .tokens import AuditedTokenObtainPairSerializer, revoke_all_refresh_tokens


# --------------------------------------------------------------------------- session

class AuditedTokenObtainPairView(TokenObtainPairView):
    serializer_class = AuditedTokenObtainPairSerializer


class LogoutView(APIView):
    """POST {refresh}: blacklist the caller's refresh token (server-side logout)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
        except TokenError:
            # Already expired/blacklisted: the session is over either way.
            return Response(status=status.HTTP_205_RESET_CONTENT)
        if str(token.get('user_id')) != str(request.user.pk):
            return Response({'detail': 'This token does not belong to you.'}, status=status.HTTP_403_FORBIDDEN)
        token.blacklist()
        audit(
            request,
            AuditLog.Action.LOGOUT,
            USER_ENTITY,
            user=request.user,
            entity_id=request.user.pk,
            outcome=AuditLog.Outcome.SUCCESS,
        )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    """GET: own account, role, job title and capabilities. PATCH: own contact details."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.user.refresh_from_db()
        return Response(MeSerializer(request.user).data)


class ChangePasswordView(APIView):
    """POST {current_password, new_password}. Signs the user out everywhere afterwards."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        revoke_all_refresh_tokens(user)
        return Response({'detail': 'Password changed. Please sign in again with your new password.'})


GENERIC_RESET_MESSAGE = ('If an active account uses that email address, a password reset link '
                         'has been sent to it.')


class PasswordResetRequestView(APIView):
    """POST {email}. Always answers the same way, so it never reveals whether an email exists."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        users = User.objects.filter(email__iexact=email, is_active=True)
        for user in users:
            if not user.has_usable_password():
                continue
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject='LiverLink password reset',
                message=(
                    f'Hello {user.get_full_name() or user.username},\n\n'
                    'We received a request to reset the password of your LiverLink account '
                    f'"{user.username}".\nUse this link to choose a new password:\n\n{link}\n\n'
                    'If you did not ask for this, you can ignore this email. The link expires automatically.\n'
                ),
                from_email=None,
                recipient_list=[user.email],
            )
        return Response({'detail': GENERIC_RESET_MESSAGE})


class PasswordResetConfirmView(APIView):
    """POST {uid, token, new_password}."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    @transaction.atomic
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        invalid = Response({'detail': 'This password reset link is invalid or has expired.'},
                           status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data['uid'])), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return invalid
        if not default_token_generator.check_token(user, data['token']):
            return invalid
        try:
            validate_password(data['new_password'], user)
        except DjangoValidationError as exc:
            return Response({'new_password': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(data['new_password'])
        user.save(update_fields=['password'])  # also invalidates the reset token
        revoke_all_refresh_tokens(user)
        return Response({'detail': 'Your password has been reset. You can now sign in.'})


# --------------------------------------------------------------------------- user management

USER_ENTITY = 'accounts.user'


def _account_snapshot(user):
    """Current stored values of an account and its staff profile, used only to detect a change."""
    user = User.objects.select_related('staff_profile').get(pk=user.pk)
    rows = [user, getattr(user, 'staff_profile', None)]
    return [{f.attname: getattr(row, f.attname) for f in row._meta.concrete_fields} if row else None
            for row in rows]


class UserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/users/?search=&role=&job_title=&is_active=   list all accounts (super_admin)
    POST /api/users/                                        create a staff account (super_admin)
    """

    permission_classes = [IsAuthenticated, HasCapability('users.manage')]
    pagination_class = UserPagination

    def get_queryset(self):
        qs = User.objects.select_related('staff_profile').order_by('username')
        params = self.request.query_params
        if search := params.get('search', '').strip():
            qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search)
                           | Q(first_name__icontains=search) | Q(last_name__icontains=search))
        if role := params.get('role'):
            qs = qs.filter(role=role)
        if job_title := params.get('job_title'):
            qs = qs.filter(staff_profile__job_title=job_title)
        if (active := params.get('is_active')) in ('true', 'false'):
            qs = qs.filter(is_active=(active == 'true'))
        if (has_profile := params.get('has_staff_profile')) in ('true', 'false'):
            qs = qs.filter(staff_profile__isnull=(has_profile == 'false'))
        if (ordering := params.get('ordering')) in self.ORDERINGS:
            qs = qs.order_by(ordering, 'username')
        return qs

    ORDERINGS = ('username', '-username', 'date_joined', '-date_joined', 'last_login', '-last_login')

    def get_serializer_class(self):
        return StaffAccountCreateSerializer if self.request.method == 'POST' else UserListSerializer

    def create(self, request, *args, **kwargs):
        serializer = StaffAccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        audit(request, AuditLog.Action.CREATE, USER_ENTITY, entity_id=user.pk)
        return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /api/users/<id>/ (super_admin). PUT is not supported."""

    permission_classes = [IsAuthenticated, HasCapability('users.manage')]
    queryset = User.objects.select_related('staff_profile')
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        return UserDetailSerializer

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = StaffAccountUpdateSerializer(user, data=request.data, partial=True,
                                                  context={'request': request})
        serializer.is_valid(raise_exception=True)
        before = _account_snapshot(user)
        serializer.save()
        if _account_snapshot(user) != before:  # a no-op PATCH is not logged
            audit(request, AuditLog.Action.UPDATE, USER_ENTITY, entity_id=user.pk)
        user = User.objects.select_related('staff_profile').get(pk=user.pk)
        return Response(UserDetailSerializer(user).data)


class _SetActiveView(APIView):
    permission_classes = [IsAuthenticated, HasCapability('users.manage')]
    make_active = None

    @transaction.atomic
    def post(self, request, pk):
        user = generics.get_object_or_404(User.objects.select_for_update(), pk=pk)
        if user.pk == request.user.pk:
            return Response({'detail': 'You cannot change the activation of your own account.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser and not request.user.is_superuser:
            return Response({'detail': 'Only a system superuser can change a superuser account.'},
                            status=status.HTTP_403_FORBIDDEN)
        if user.is_active != self.make_active:
            user.is_active = self.make_active
            user.save(update_fields=['is_active'])
            if not self.make_active:
                revoke_all_refresh_tokens(user)
            action = AuditLog.Action.ACTIVATE if self.make_active else AuditLog.Action.DEACTIVATE
            audit(request, action, USER_ENTITY, entity_id=user.pk)
        user = User.objects.select_related('staff_profile').get(pk=user.pk)
        return Response(UserDetailSerializer(user).data)


class UserActivateView(_SetActiveView):
    make_active = True


class UserDeactivateView(_SetActiveView):
    make_active = False


# --------------------------------------------------------------------------- audit log viewer

class AuditLogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/audit-logs/ (audit.view: Super Admin only). Read-only, newest first, paginated.

    Filters (all optional): action, kind=read|write, user (id), patient (id or patient_mrn),
    entity_type, entity_id, actor (username), outcome, date_from / date_to (YYYY-MM-DD, inclusive,
    UTC). Invalid filters return 400.
    Only GET is allowed: entries can never be created, changed or deleted through the API.
    Viewing the log is itself not logged (list views are outside the audit policy).
    """

    permission_classes = [IsAuthenticated, HasCapability('audit.view')]
    serializer_class = AuditLogSerializer
    pagination_class = AuditLogPagination
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        filters = AuditLogFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        f = filters.validated_data
        qs = AuditLog.objects.select_related('patient')
        if 'action' in f:
            qs = qs.filter(action=f['action'])
        if 'kind' in f:
            reads = Q(action__in=AuditLog.READ_ACTIONS)
            qs = qs.filter(reads if f['kind'] == 'read' else ~reads)
        if 'user' in f:
            qs = qs.filter(user_id=f['user'])
        if 'actor' in f:
            qs = qs.filter(actor__icontains=f['actor'])
        if 'outcome' in f:
            qs = qs.filter(outcome=f['outcome'])
        if 'patient' in f:
            qs = qs.filter(patient_id=f['patient'])
        if 'patient_mrn' in f:
            qs = qs.filter(patient__mrn__iexact=f['patient_mrn'])
        if 'entity_type' in f:
            qs = qs.filter(entity_type=f['entity_type'].strip())
        if 'entity_id' in f:
            qs = qs.filter(entity_id=f['entity_id'])
        if 'date_from' in f:
            qs = qs.filter(timestamp__date__gte=f['date_from'])
        if 'date_to' in f:
            qs = qs.filter(timestamp__date__lte=f['date_to'])
        return qs.order_by('-timestamp', '-id')

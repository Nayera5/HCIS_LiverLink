// Small stroke icons (24px grid, inherit currentColor).

function Svg({ children, className = '', size = 20, ...rest }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  )
}

export const EyeIcon = (p) => (
  <Svg {...p}>
    <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" />
    <circle cx="12" cy="12" r="3" />
  </Svg>
)

export const EyeOffIcon = (p) => (
  <Svg {...p}>
    <path d="M10.6 5.1A10.4 10.4 0 0 1 12 5c6.4 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.1" />
    <path d="M6.6 6.6C3.7 8.5 2 12 2 12s3.6 7 10 7a9.7 9.7 0 0 0 5.4-1.6" />
    <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    <path d="m2 2 20 20" />
  </Svg>
)

export const ClockIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </Svg>
)

export const CalendarIcon = (p) => (
  <Svg {...p}>
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M3 10h18M8 3v4M16 3v4" />
  </Svg>
)

export const AlertCircleIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v5" />
    <path d="M12 16.2v.1" />
  </Svg>
)

export const CheckCircleIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="m8.5 12.2 2.4 2.4 4.6-4.9" />
  </Svg>
)

export const LockIcon = (p) => (
  <Svg {...p}>
    <rect x="5" y="11" width="14" height="10" rx="2" />
    <path d="M8 11V7a4 4 0 0 1 8 0v4" />
  </Svg>
)

export const GridIcon = (p) => (
  <Svg {...p}>
    <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
    <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
    <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
    <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
  </Svg>
)

export const UsersIcon = (p) => (
  <Svg {...p}>
    <circle cx="9" cy="8" r="3.5" />
    <path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" />
    <path d="M16 4.6a3.5 3.5 0 0 1 0 6.8" />
    <path d="M18.5 14.4c1.9.8 3 2.8 3 5.6" />
  </Svg>
)

export const UserIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 20.5c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" />
  </Svg>
)

export const LogOutIcon = (p) => (
  <Svg {...p}>
    <path d="M9 4H5.5A1.5 1.5 0 0 0 4 5.5v13A1.5 1.5 0 0 0 5.5 20H9" />
    <path d="M15.5 16.5 20 12l-4.5-4.5" />
    <path d="M20 12H9" />
  </Svg>
)

export const PlusIcon = (p) => (
  <Svg {...p}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
)

export const SearchIcon = (p) => (
  <Svg {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </Svg>
)

export const MenuIcon = (p) => (
  <Svg {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Svg>
)

export const CloseIcon = (p) => (
  <Svg {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Svg>
)

export const ChevronLeftIcon = (p) => (
  <Svg {...p}>
    <path d="m15 18-6-6 6-6" />
  </Svg>
)

export const ShieldIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3 19.5 6v6c0 4.4-3.1 7.7-7.5 9-4.4-1.3-7.5-4.6-7.5-9V6Z" />
    <path d="m9 12 2 2 4-4" />
  </Svg>
)

export const KeyIcon = (p) => (
  <Svg {...p}>
    <circle cx="8" cy="15" r="4" />
    <path d="m11 12 9-9M17 6l3 3M14.5 8.5l2 2" />
  </Svg>
)

export const MailIcon = (p) => (
  <Svg {...p}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="m4 7 8 6 8-6" />
  </Svg>
)

export const InfoIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5" />
    <path d="M12 7.8v.1" />
  </Svg>
)

export const UserPlusIcon = (p) => (
  <Svg {...p}>
    <circle cx="9" cy="8" r="3.5" />
    <path d="M2.5 20c0-3.6 2.9-6 6.5-6 1.7 0 3.3.5 4.4 1.5" />
    <path d="M18 14v6M15 17h6" />
  </Svg>
)

export const AlertTriangleIcon = (p) => (
  <Svg {...p}>
    <path d="M10.3 4.2 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z" />
    <path d="M12 9.5v4.5" />
    <path d="M12 17.2v.1" />
  </Svg>
)

export const ClipboardIcon = (p) => (
  <Svg {...p}>
    <rect x="5" y="4.5" width="14" height="16.5" rx="2" />
    <path d="M9 4.5V3.5h6v1" />
    <path d="M9 11h6M9 15h4" />
  </Svg>
)

export const HeartPulseIcon = (p) => (
  <Svg {...p}>
    <path d="M20.4 12.2 12 20.5l-8.4-8.3A5 5 0 0 1 12 6a5 5 0 0 1 8.4 6.2Z" />
    <path d="M3.5 12h4l2-3 3 5 2-2h5" />
  </Svg>
)

export const FlaskIcon = (p) => (
  <Svg {...p}>
    <path d="M9.5 3.5h5M10.5 3.5v6L5 19a1.6 1.6 0 0 0 1.4 2.4h11.2A1.6 1.6 0 0 0 19 19l-5.5-9.5v-6" />
    <path d="M7.8 15h8.4" />
  </Svg>
)

export const ScanIcon = (p) => (
  <Svg {...p}>
    <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
    <circle cx="12" cy="12" r="3.5" />
  </Svg>
)

export const PillIcon = (p) => (
  <Svg {...p}>
    <path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z" />
    <path d="m8.5 8.5 7 7" />
  </Svg>
)

export const TargetIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="5" />
    <circle cx="12" cy="12" r="1" />
  </Svg>
)

export const ReceiptIcon = (p) => (
  <Svg {...p}>
    <path d="M6 3h12v18l-2.5-1.5L13 21l-2.5-1.5L8 21l-2-1.5Z" />
    <path d="M9 8h6M9 12h6M9 16h4" />
  </Svg>
)

export const CreditCardIcon = (p) => (
  <Svg {...p}>
    <rect x="3" y="5.5" width="18" height="13" rx="2" />
    <path d="M3 10h18" />
    <path d="M7 14.5h4" />
  </Svg>
)

export const BellIcon = (p) => (
  <Svg {...p}>
    <path d="M6 10a6 6 0 0 1 12 0c0 4 1.5 5.5 2 6H4c.5-.5 2-2 2-6Z" />
    <path d="M10 19a2 2 0 0 0 4 0" />
  </Svg>
)

export const BarChartIcon = (p) => (
  <Svg {...p}>
    <path d="M4 20h16" />
    <path d="M7 16v-5M12 16V6M17 16v-8" />
  </Svg>
)

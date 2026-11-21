// Decorative liver illustration: a glowing liver silhouette with a node-and-edge mesh.
// Pure SVG, computed once at module load; it is hidden from assistive technology.

const LIVER_PATH =
  'M70 95C90 50 160 42 230 42C320 42 400 60 445 85C462 95 462 112 445 125' +
  'C400 165 330 215 250 260C200 288 160 305 128 300C95 295 75 265 66 220C58 180 55 130 70 95Z'

// Deterministic pseudo-random generator so the mesh is identical on every render.
function seeded(seed) {
  let s = seed
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

function buildMesh() {
  const rand = seeded(42)
  const points = []
  for (let y = 40; y <= 310; y += 38) {
    for (let x = 50; x <= 470; x += 44) {
      points.push({
        x: x + (rand() - 0.5) * 30 + ((y / 38) % 2) * 18,
        y: y + (rand() - 0.5) * 24,
        bright: rand() > 0.72,
      })
    }
  }
  const edges = []
  points.forEach((p, i) => {
    points
      .map((q, j) => ({ j, d: Math.hypot(p.x - q.x, p.y - q.y) }))
      .filter(({ j, d }) => j > i && d < 66)
      .sort((a, b) => a.d - b.d)
      .slice(0, 4)
      .forEach(({ j }) => edges.push([p, points[j]]))
  })
  return { points, edges }
}

const MESH = buildMesh()

const SPECKS = [
  [-10, 18], [100, -8], [320, -12], [500, 168], [-20, 172], [10, 268], [360, 300], [470, 210],
]

function HexBadge({ x, y, children }) {
  const r = 17
  const pts = Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i - Math.PI / 2
    return `${x + r * Math.cos(a)},${y + r * Math.sin(a)}`
  }).join(' ')
  return (
    <g>
      <polygon points={pts} fill="rgba(13,40,58,0.6)" stroke="#3f8f9c" strokeWidth="1.2" />
      <g transform={`translate(${x - 7} ${y - 7})`} stroke="#7cc6cc" strokeWidth="1.4" fill="none"
        strokeLinecap="round" strokeLinejoin="round">
        {children}
      </g>
    </g>
  )
}

export default function LiverIllustration({ className = '' }) {
  return (
    <svg
      className={className}
      viewBox="-40 -30 560 370"
      role="presentation"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="ll-liver-fill" x1="0" y1="0" x2="1" y2="0.6">
          <stop offset="0" stopColor="#3cc4bf" />
          <stop offset="0.55" stopColor="#2a93a6" />
          <stop offset="1" stopColor="#2a6fa3" />
        </linearGradient>
        <radialGradient id="ll-liver-highlight" cx="0.32" cy="0.42" r="0.5">
          <stop offset="0" stopColor="#7fe3d8" stopOpacity="0.55" />
          <stop offset="1" stopColor="#7fe3d8" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="ll-glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#2fb3b4" stopOpacity="0.45" />
          <stop offset="1" stopColor="#2fb3b4" stopOpacity="0" />
        </radialGradient>
        <clipPath id="ll-liver-clip">
          <path d={LIVER_PATH} />
        </clipPath>
        <filter id="ll-soft" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="14" />
        </filter>
      </defs>

      {/* Ambient glow */}
      <ellipse cx="250" cy="170" rx="300" ry="200" fill="url(#ll-glow)" />
      <path d={LIVER_PATH} fill="#3cc4bf" opacity="0.5" filter="url(#ll-soft)" />

      {/* Liver body */}
      <path d={LIVER_PATH} fill="url(#ll-liver-fill)" />
      <path d={LIVER_PATH} fill="url(#ll-liver-highlight)" />

      {/* Mesh, clipped to the liver */}
      <g clipPath="url(#ll-liver-clip)">
        {MESH.edges.map(([a, b], i) => (
          <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#c9f4ee" strokeOpacity="0.32"
            strokeWidth="0.9" />
        ))}
        {/* Vessels */}
        <path d="M130 165C190 150 258 158 296 194" stroke="#163f5a" strokeOpacity="0.75"
          strokeWidth="5" fill="none" strokeLinecap="round" />
        <path d="M166 244C206 232 238 196 268 168" stroke="#163f5a" strokeOpacity="0.75"
          strokeWidth="5" fill="none" strokeLinecap="round" />
        {MESH.points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={p.bright ? 2.6 : 1.7} fill="#ffffff"
            opacity={p.bright ? 0.95 : 0.65} />
        ))}
      </g>

      {/* Outline */}
      <path d={LIVER_PATH} fill="none" stroke="#bff1ea" strokeOpacity="0.85" strokeWidth="1.6" />

      {/* Connectors */}
      <g stroke="#4b97a3" strokeOpacity="0.7" strokeWidth="1" strokeDasharray="3 4" fill="none">
        <path d="M44 86L74 112" />
        <path d="M462 46L430 82" />
        <path d="M444 242L400 196" />
      </g>

      <HexBadge x={28} y={73}>
        <rect x="2.5" y="6" width="9" height="7" rx="1.2" />
        <path d="M4.5 6V4.2a2.5 2.5 0 0 1 5 0V6" />
      </HexBadge>
      <HexBadge x={474} y={34}>
        <path d="M7 1.5 12 3.5v3.8c0 3-2.2 5-5 5.9-2.8-.9-5-2.9-5-5.9V3.5Z" />
      </HexBadge>
      <HexBadge x={453} y={254}>
        <path d="m3.5 7.2 2.4 2.4 4.6-4.9" />
      </HexBadge>

      {SPECKS.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="2" fill="#5fa9b4" opacity="0.7" />
      ))}
    </svg>
  )
}

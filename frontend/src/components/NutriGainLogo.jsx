export default function NutriGainLogo({ size = "md", showText = true, theme = "light" }) {
  const isLarge = size === "lg";
  const width = isLarge ? 230 : 180;
  const height = isLarge ? 54 : 42;

  const nutriColor = theme === "dark" ? "#ffffff" : "#166534";
  const subColor = theme === "dark" ? "#cbd5e1" : "#5f7d98";

  return (
    <div className={`nutrigain-logo ${size} flex items-center gap-3`}>
      <svg
        viewBox="0 0 120 120"
        width={isLarge ? 44 : 36}
        height={isLarge ? 44 : 36}
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="ngCore" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#22c55e" />
            <stop offset="100%" stopColor="#2563eb" />
          </linearGradient>
        </defs>
        <rect x="6" y="6" width="108" height="108" rx="28" fill="url(#ngCore)" />
        <path d="M95 24c-40 0-70 25-70 60 0 15 10 25 25 25 35 0 50-40 45-85z" fill="none" stroke="#ffffff" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M30 96c15-20 31-31 54-42" fill="none" stroke="#ffffff" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {showText ? (
        <svg viewBox="0 0 360 70" width={width} height={height} aria-label="NutriGain logo">
          <g fill="none" fillRule="evenodd">
            <text x="2" y="44" fill={nutriColor} fontSize="38" fontFamily="Nunito, sans-serif" fontWeight="800">
              Nutri
            </text>
            <text x="108" y="44" fill="#2563eb" fontSize="38" fontFamily="Nunito, sans-serif" fontWeight="800">
              Gain
            </text>
            <text x="4" y="63" fill={subColor} fontSize="14" fontFamily="Source Sans 3, sans-serif" fontWeight="700" letterSpacing="1.2">
              BUILD HEALTHY CALORIES
            </text>
          </g>
        </svg>
      ) : null}
    </div>
  );
}

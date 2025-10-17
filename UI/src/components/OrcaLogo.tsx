export function OrcaLogo({ isSmall }: { isSmall?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex items-center gap-3">
        {/* Whale SVG */}
        <svg
          width={isSmall ? "32" : "64"}
          height={isSmall ? "32" : "64"}
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="transition-all duration-700"
        >
          <path
            d="M52 28C52 28 48 18 40 16C32 14 28 14 22 16C16 18 8 24 6 32C4 40 6 44 10 46C14 48 16 48 18 46C20 44 20 42 18 40C16 38 14 36 14 32C14 28 16 24 20 22C24 20 28 20 32 22C36 24 40 28 42 32C44 36 44 40 42 42C40 44 38 44 36 42C34 40 34 38 36 36C38 34 40 34 42 36"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-cyan-300"
          />
          <circle
            cx="38"
            cy="24"
            r="2"
            fill="currentColor"
            className="text-cyan-200"
          />
          <path
            d="M48 32C48 32 52 34 54 36C56 38 58 40 58 42"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            className="text-cyan-400 opacity-70"
          />
        </svg>
        <h1
          className={`${
            isSmall ? "text-3xl" : "text-7xl"
          } transition-all duration-700 tracking-wider text-cyan-100`}
          style={{ fontFamily: "'Archivo Black', system-ui, sans-serif" }}
        >
          ORCA
        </h1>
      </div>
      {!isSmall && (
        <p
          className="text-cyan-300/80 text-center max-w-md transition-opacity duration-500"
          style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
        >
          Automated competitor extraction • Dive deep, surface insights
        </p>
      )}
    </div>
  );
}

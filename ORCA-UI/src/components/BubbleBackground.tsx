import { useEffect, useRef } from "react";

interface Bubble {
  id: number;
  x: number;
  size: number;
  duration: number;
  drift: number;
  delay: number;
}

const BubbleBackground = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const bubblesRef = useRef<Bubble[]>([]);

  useEffect(() => {
    // Generate 8 small bubbles with random distribution
    const bubbles: Bubble[] = [];
    for (let i = 0; i < 8; i++) {
      bubbles.push({
        id: i,
        x: Math.random() * 100, // Random distribution
        size: 6 + Math.random() * 10, // 6-16px (smaller)
        duration: 25 + Math.random() * 25, // 25-50 seconds (slower)
        drift: -15 + Math.random() * 30, // -15px to +15px horizontal drift
        delay: Math.random() * 15, // Stagger start times
      });
    }
    bubblesRef.current = bubbles;
  }, []);

  return (
    <div ref={containerRef} className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {bubblesRef.current.map((bubble) => (
        <div
          key={bubble.id}
          className="bubble animate-bubble-rise"
          style={{
            left: `${bubble.x}%`,
            bottom: "-50px",
            width: `${bubble.size}px`,
            height: `${bubble.size}px`,
            opacity: 0.15 + Math.random() * 0.2, // Lower opacity (0.15-0.35)
            animationDuration: `${bubble.duration}s`,
            animationDelay: `${bubble.delay}s`,
            // @ts-ignore - CSS custom properties
            "--drift": `${bubble.drift}px`,
          }}
        />
      ))}
    </div>
  );
};

export default BubbleBackground;

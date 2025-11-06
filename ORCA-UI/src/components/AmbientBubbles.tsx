import { useEffect, useRef } from 'react';

const AmbientBubbles = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let bubbles = [];

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Bubble class
    class Bubble {
      constructor() {
        this.reset();
        this.y = Math.random() * canvas.height;
        this.opacity = Math.random() * 0.3 + 0.1;
      }

      reset() {
        this.x = Math.random() * canvas.width;
        this.y = canvas.height + 20;
        this.size = Math.random() * 3 + 1; // Very small: 1-4px
        this.speedY = Math.random() * 0.5 + 0.3; // Slow rise
        this.speedX = (Math.random() - 0.5) * 0.3; // Gentle drift
        this.opacity = Math.random() * 0.3 + 0.1; // Very subtle
        this.life = Math.random() * 300 + 200; // Lifespan
        this.age = 0;
        this.hue = Math.random() * 60 + 180; // Blue-cyan range
      }

      update() {
        this.y -= this.speedY;
        this.x += this.speedX;
        this.age++;

        // Fade out near end of life
        if (this.age > this.life * 0.7) {
          this.opacity *= 0.98;
        }

        // Reset if off screen or too old
        if (this.y < -20 || this.age > this.life || this.x < -20 || this.x > canvas.width + 20) {
          this.reset();
        }
      }

      draw(isDark) {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        
        // Adjust colors for theme
        const lightness = isDark ? 70 : 50;
        const saturation = isDark ? 60 : 40;
        
        // Gradient for glow effect
        const gradient = ctx.createRadialGradient(
          this.x, this.y, 0,
          this.x, this.y, this.size * 2
        );
        gradient.addColorStop(0, `hsla(${this.hue}, ${saturation}%, ${lightness}%, ${this.opacity})`);
        gradient.addColorStop(0.5, `hsla(${this.hue}, ${saturation}%, ${lightness}%, ${this.opacity * 0.5})`);
        gradient.addColorStop(1, `hsla(${this.hue}, ${saturation}%, ${lightness}%, 0)`);
        
        ctx.fillStyle = gradient;
        ctx.fill();
      }
    }

    // Create bubbles (not too many - about 30)
    for (let i = 0; i < 30; i++) {
      bubbles.push(new Bubble());
    }

    // Check theme
    const isDarkTheme = () => {
      return document.documentElement.classList.contains('dark');
    };

    // Animation loop
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const isDark = isDarkTheme();
      
      bubbles.forEach(bubble => {
        bubble.update();
        bubble.draw(isDark);
      });

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    // Cleanup
    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 1 }}
    />
  );
};

export default AmbientBubbles;
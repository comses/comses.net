(() => {
  const canvas = document.getElementById("hex-animation");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const hexagons = [];
  let width = 0,
    height = 0,
    animationId;

  const TARGET_FPS = 10;
  const FRAME_INTERVAL = 1000 / TARGET_FPS;
  const SPEED_MULTIPLIER = 5;
  const NUM_HEXAGONS = 15;

  // pre-calculated hexagon vertices (unit circle)
  const HEX_VERTICES = Array.from({ length: 6 }, (_, i) => {
    const angle = (Math.PI / 3) * i;
    return { x: Math.cos(angle), y: Math.sin(angle) };
  });

  class Hexagon {
    constructor() {
      this.radius = 50 + Math.random() * 225;
      this.x = Math.random() * (width + this.radius * 2) - this.radius;
      this.y = Math.random() * (height + this.radius * 2) - this.radius;

      const angle = Math.random() * Math.PI * 2;
      const speed = (0.1 + Math.random() * 0.15) * SPEED_MULTIPLIER;
      this.vx = Math.cos(angle) * speed;
      this.vy = Math.sin(angle) * speed;

      this.opacity = 0.02 + Math.random() * 0.15;
      // this.blur = this.getBlur();
      this.hasGradient = Math.random() < 0.5;
      this.fillStyle = this.hasGradient ? null : `rgba(255,255,255,${this.opacity})`;
      this.gradient = null;
    }

    // getBlur() {
    //   const rand = Math.random();
    //   if (rand < 0.4) return 0;
    //   if (rand < 0.6) return 0.5 + Math.random();
    //   if (rand < 0.8) return 1.5 + Math.random() * 1.5;
    //   return 3 + Math.random() * 2;
    // }

    update() {
      this.x += this.vx;
      this.y += this.vy;

      // wrap around boundaries
      if (this.x < -this.radius) this.x = width + this.radius;
      else if (this.x > width + this.radius) this.x = -this.radius;

      if (this.y < -this.radius) this.y = height + this.radius;
      else if (this.y > height + this.radius) this.y = -this.radius;
    }

    draw(ctx) {
      // Apply blur if needed
      // if (this.blur > 0) {
      //   ctx.save();
      //   ctx.filter = `blur(${this.blur}px)`;
      // }

      // draw hexagon path
      ctx.beginPath();
      HEX_VERTICES.forEach((vertex, i) => {
        const x = this.x + vertex.x * this.radius;
        const y = this.y + vertex.y * this.radius;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.closePath();

      // fill style
      if (this.hasGradient) {
        if (!this.gradient) {
          this.gradient = ctx.createLinearGradient(
            this.x - this.radius,
            this.y,
            this.x + this.radius,
            this.y
          );
          this.gradient.addColorStop(0, `rgba(255,255,255,${this.opacity})`);
          this.gradient.addColorStop(1, `rgba(255,255,255,0)`);
        }
        ctx.fillStyle = this.gradient;
      } else {
        ctx.fillStyle = this.fillStyle;
      }

      ctx.fill();

      // if (this.blur > 0) ctx.restore();
    }
  }

  function setupCanvas() {
    const parent = canvas.parentElement;
    const rect = parent.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    width = rect.width > 0 ? rect.width : window.innerWidth;
    height = rect.height > 0 ? rect.height : window.innerHeight;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";

    ctx.scale(dpr, dpr);
    return width > 0 && height > 0;
  }

  function createHexagons() {
    hexagons.length = 0;
    for (let i = 0; i < NUM_HEXAGONS; i++) {
      hexagons.push(new Hexagon());
    }
  }

  let lastTime = 0;
  function animate(currentTime = 0) {
    if (document.hidden || currentTime - lastTime < FRAME_INTERVAL) {
      animationId = requestAnimationFrame(animate);
      return;
    }

    lastTime = currentTime;
    ctx.clearRect(0, 0, width, height);

    hexagons.forEach(hex => {
      hex.update();
      hex.draw(ctx);
    });

    animationId = requestAnimationFrame(animate);
  }

  function initialize() {
    if (!setupCanvas()) {
      setTimeout(initialize, 50);
      return;
    }
    createHexagons();
    animate();
  }

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !animationId) animate();
  });

  let resizeTimeout;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      const oldArea = width * height;
      if (setupCanvas()) {
        const newArea = width * height;
        // only recreate hexagons if significant size change
        if (Math.abs(newArea - oldArea) / oldArea > 0.2) {
          createHexagons();
        }
      }
    }, 100);
  });

  // start when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    setTimeout(initialize, 10);
  }
})();

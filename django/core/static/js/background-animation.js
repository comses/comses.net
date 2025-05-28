document.addEventListener('DOMContentLoaded', function () {
    const canvas = document.getElementById('backgroundCanvas');
    if (!canvas) return; 
    const ctx = canvas.getContext('2d');
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;
  
    window.addEventListener('resize', () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });
  
    class Hexagon {
      constructor() {
        this.radius = 50 + Math.random() * 150;
        this.x = Math.random() * (width + this.radius * 2) - this.radius;
        this.y = Math.random() * (height + this.radius * 2) - this.radius;
        const angle = Math.random() * Math.PI * 2;
        this.vx = Math.cos(angle) * (0.2 + Math.random() * 0.3);
        this.vy = Math.sin(angle) * (0.2 + Math.random() * 0.3);
        this.opacity = 0.2 + Math.random() * 0.3;
      }
      update() {
        this.x += this.vx;
        this.y += this.vy;
        if (this.x < -this.radius) this.x = width + this.radius;
        if (this.x > width + this.radius) this.x = -this.radius;
        if (this.y < -this.radius) this.y = height + this.radius;
        if (this.y > height + this.radius) this.y = -this.radius;
      }
      draw(ctx) {
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
          const theta = (Math.PI / 3) * i;
          const x_i = this.x + this.radius * Math.cos(theta);
          const y_i = this.y + this.radius * Math.sin(theta);
          if (i === 0) {
            ctx.moveTo(x_i, y_i);
          } else {
            ctx.lineTo(x_i, y_i);
          }
        }
        ctx.closePath();
        ctx.fillStyle = `rgba(255, 255, 255, ${this.opacity})`; 
        ctx.fill();
      }
    }
  
    const hexagons = [];
    const count = 20;
    for (let i = 0; i < count; i++) {
      hexagons.push(new Hexagon());
    }
  
    function animate() {
      requestAnimationFrame(animate);
      ctx.clearRect(0, 0, width, height);
      hexagons.forEach(hex => {
        hex.update();
        hex.draw(ctx);
      });
    }
  
    animate();
  });
  
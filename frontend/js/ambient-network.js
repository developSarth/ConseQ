/**
 * ConseQ / ECHO — Subtle Ambient Network Background
 * Lightweight, 100% non-intrusive background canvas (pointer-events: none).
 * Displays a delicate constellation of architectural nodes that gently drift,
 * with subtle pulses when simulations run.
 */

class AmbientNetworkBackground {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.particles = [];
    this.connections = [];
    this.pulseWave = null;
    this.activeColor = '#38bdf8';
    
    this.resize();
    this.initParticles();
    this.startLoop();

    window.addEventListener('resize', () => {
      this.resize();
      this.initParticles();
    });
  }

  resize() {
    if (!this.canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  initParticles() {
    this.particles = [];
    const count = Math.min(Math.floor((this.width * this.height) / 22000), 55);

    for (let i = 0; i < count; i++) {
      this.particles.push({
        x: Math.random() * this.width,
        y: Math.random() * this.height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: 1.5 + Math.random() * 2,
        baseAlpha: 0.15 + Math.random() * 0.2,
        pulseOffset: Math.random() * Math.PI * 2,
      });
    }
  }

  triggerPulse(type = 'failure') {
    this.activeColor = type === 'failure' ? '#f43f5e' : (type === 'upgrade' ? '#f59e0b' : '#10b981');
    this.pulseWave = {
      x: this.width * 0.5,
      y: this.height * 0.35,
      radius: 0,
      maxRadius: Math.hypot(this.width, this.height) * 0.65,
      opacity: 0.6
    };
  }

  startLoop() {
    let lastTime = performance.now();
    const frame = (now) => {
      const dt = (now - lastTime) * 0.001;
      lastTime = now;
      this.update(dt);
      this.render();
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  }

  update(dt) {
    const t = performance.now() * 0.001;
    this.particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0) p.x = this.width;
      if (p.x > this.width) p.x = 0;
      if (p.y < 0) p.y = this.height;
      if (p.y > this.height) p.y = 0;
    });

    if (this.pulseWave) {
      this.pulseWave.radius += 320 * dt;
      this.pulseWave.opacity = Math.max(0, 0.6 * (1 - this.pulseWave.radius / this.pulseWave.maxRadius));
      if (this.pulseWave.radius >= this.pulseWave.maxRadius) {
        this.pulseWave = null;
      }
    }
  }

  render() {
    this.ctx.clearRect(0, 0, this.width, this.height);

    // Render Connections between close ambient nodes
    const maxDist = 140;
    const count = this.particles.length;

    for (let i = 0; i < count; i++) {
      const p1 = this.particles[i];
      for (let j = i + 1; j < count; j++) {
        const p2 = this.particles[j];
        const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
        if (dist < maxDist) {
          const alpha = (1 - dist / maxDist) * 0.08;
          this.ctx.beginPath();
          this.ctx.moveTo(p1.x, p1.y);
          this.ctx.lineTo(p2.x, p2.y);
          this.ctx.strokeStyle = `rgba(56, 189, 248, ${alpha})`;
          this.ctx.lineWidth = 0.8;
          this.ctx.stroke();
        }
      }
    }

    // Render Ambient Nodes
    this.particles.forEach(p => {
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = `rgba(129, 140, 248, ${p.baseAlpha})`;
      this.ctx.fill();
    });

    // Render Shockwave Ripple if active
    if (this.pulseWave) {
      this.ctx.beginPath();
      this.ctx.arc(this.pulseWave.x, this.pulseWave.y, this.pulseWave.radius, 0, Math.PI * 2);
      this.ctx.strokeStyle = this.activeColor;
      this.ctx.globalAlpha = this.pulseWave.opacity;
      this.ctx.lineWidth = 2.5;
      this.ctx.stroke();
      this.ctx.globalAlpha = 1.0;
    }
  }
}

window.AmbientNetworkBackground = AmbientNetworkBackground;

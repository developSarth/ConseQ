/**
 * ConseQ / ECHO — Interactive Architecture Graph Visualizer
 * High-performance HTML5 Canvas with DPI scaling, physics layout,
 * cascading shockwave pulses, hover tooltips, and pan/zoom.
 */

class GraphVisualizer {
  constructor(canvasId, containerId) {
    this.canvas = document.getElementById(canvasId);
    this.container = document.getElementById(containerId);
    this.ctx = this.canvas.getContext('2d');
    
    this.nodes = [];
    this.links = [];
    this.nodeMap = new Map();
    
    // Viewport transform
    this.scale = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.isDragging = false;
    this.lastMouse = { x: 0, y: 0 };
    this.hoveredNode = null;
    
    // Animation state
    this.animTime = 0;
    this.pulsePhase = 0;
    this.simulationState = null; // Holds active report details
    this.rippleShockwaves = [];
    
    this.initEvents();
    this.resize();
    this.startLoop();
  }

  resize() {
    if (!this.container || !this.canvas) return;
    const rect = this.container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.width = rect.width;
    this.height = rect.height;
    
    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.canvas.style.width = `${this.width}px`;
    this.canvas.style.height = `${this.height}px`;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  initEvents() {
    window.addEventListener('resize', () => this.resize());

    // Mouse drag for panning
    this.canvas.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      this.lastMouse = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (this.isDragging) {
        this.panX += e.clientX - this.lastMouse.x;
        this.panY += e.clientY - this.lastMouse.y;
        this.lastMouse = { x: e.clientX, y: e.clientY };
      } else {
        // Hit-test hovered node
        this.checkHover(mouseX, mouseY);
      }
    });

    window.addEventListener('mouseup', () => {
      this.isDragging = false;
    });

    // Zooming with mouse wheel ONLY when Ctrl / Cmd is pressed
    // This prevents hijacking the page scroll when scrolling through the document
    this.canvas.addEventListener('wheel', (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
        const newScale = Math.min(Math.max(this.scale * zoomFactor, 0.4), 2.5);
        
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        this.panX = mouseX - (mouseX - this.panX) * (newScale / this.scale);
        this.panY = mouseY - (mouseY - this.panY) * (newScale / this.scale);
        this.scale = newScale;
      }
    }, { passive: false });

    // Touch support for mobile
    let lastTouchDist = 0;
    this.canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      } else if (e.touches.length === 2) {
        lastTouchDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
      }
    });

    this.canvas.addEventListener('touchmove', (e) => {
      if (e.touches.length === 1 && this.isDragging) {
        this.panX += e.touches[0].clientX - this.lastMouse.x;
        this.panY += e.touches[0].clientY - this.lastMouse.y;
        this.lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      } else if (e.touches.length === 2) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const factor = dist / (lastTouchDist || dist);
        this.scale = Math.min(Math.max(this.scale * factor, 0.4), 2.5);
        lastTouchDist = dist;
      }
    });

    this.canvas.addEventListener('touchend', () => {
      this.isDragging = false;
    });
  }

  checkHover(screenX, screenY) {
    const worldX = (screenX - this.panX) / this.scale;
    const worldY = (screenY - this.panY) / this.scale;

    let hit = null;
    for (let i = this.nodes.length - 1; i >= 0; i--) {
      const node = this.nodes[i];
      const r = node.radius || 22;
      const dist = Math.hypot(worldX - node.x, worldY - node.y);
      if (dist <= r) {
        hit = node;
        break;
      }
    }
    this.hoveredNode = hit;
    this.canvas.style.cursor = hit ? 'pointer' : (this.isDragging ? 'grabbing' : 'grab');
  }

  setData(topologyData) {
    if (!topologyData || !topologyData.nodes) return;
    this.nodes = [];
    this.links = [];
    this.nodeMap.clear();

    const rawNodes = topologyData.nodes;
    const rawLinks = topologyData.links || [];

    const layers = {
      ClientApp: [],
      APIEndpoint: [],
      Service_Tier1: [],
      Service_Tier2: [],
      Service_Tier3: [],
      Database: [],
      ThirdParty: [],
      Library: [],
      Other: []
    };

    rawNodes.forEach(node => {
      if (node.label === 'ClientApp') layers.ClientApp.push(node);
      else if (node.label === 'APIEndpoint') layers.APIEndpoint.push(node);
      else if (node.label === 'Service') {
        const tier = node.tier || 2;
        if (tier === 1) layers.Service_Tier1.push(node);
        else if (tier === 3) layers.Service_Tier3.push(node);
        else layers.Service_Tier2.push(node);
      } else if (node.label === 'Database') layers.Database.push(node);
      else if (node.label === 'ThirdParty') layers.ThirdParty.push(node);
      else if (node.label === 'Library') layers.Library.push(node);
      else layers.Other.push(node);
    });

    const columnOrder = [
      { key: 'ClientApp', col: 0 },
      { key: 'APIEndpoint', col: 1 },
      { key: 'Service_Tier1', col: 2 },
      { key: 'Service_Tier2', col: 3 },
      { key: 'Service_Tier3', col: 4 },
      { key: 'Database', col: 5 },
      { key: 'ThirdParty', col: 6 },
      { key: 'Library', col: 4 }
    ];

    const colWidth = 155;
    const startX = 80;
    const startY = 48;

    columnOrder.forEach(({ key, col }) => {
      const group = layers[key];
      if (!group) return;
      const count = group.length;
      const spacing = Math.max(50, Math.min(65, 420 / (count + 1)));

      group.forEach((rawNode, idx) => {
        let x = startX + col * colWidth;
        let y = startY + (idx + 1) * spacing;
        
        if (key === 'Library') {
          y = 310 + (idx * 60);
        }

        const node = {
          ...rawNode,
          x,
          y,
          radius: rawNode.label === 'Service' ? 22 : (rawNode.label === 'ClientApp' ? 20 : 17),
          baseColor: this.getNodeColor(rawNode),
          pulseOffset: Math.random() * Math.PI * 2,
          isAffected: false,
          isTarget: false,
          hops: 0
        };
        this.nodes.push(node);
        this.nodeMap.set(node.id, node);
      });
    });

    // Map links
    rawLinks.forEach(rawLink => {
      const source = this.nodeMap.get(rawLink.source);
      const target = this.nodeMap.get(rawLink.target);
      if (source && target) {
        this.links.push({
          source,
          target,
          type: rawLink.type,
          isBroken: false,
          speed: 0.5 + Math.random() * 0.5,
          offset: Math.random()
        });
      }
    });

    this.resetCamera();
  }

  getNodeColor(node) {
    switch (node.label) {
      case 'Service':
        return node.tier === 1 ? '#38bdf8' : (node.tier === 2 ? '#818cf8' : '#a78bfa');
      case 'Database':
        return '#fbbf24'; // Amber
      case 'ThirdParty':
        return '#ec4899'; // Pink/Rose
      case 'Library':
        return '#34d399'; // Emerald
      case 'ClientApp':
        return '#c084fc'; // Purple
      case 'APIEndpoint':
        return '#60a5fa'; // Light Blue
      default:
        return '#94a3b8';
    }
  }

  resetCamera() {
    if (this.nodes.length === 0) return;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    this.nodes.forEach(n => {
      minX = Math.min(minX, n.x);
      maxX = Math.max(maxX, n.x);
      minY = Math.min(minY, n.y);
      maxY = Math.max(maxY, n.y);
    });

    const graphWidth = maxX - minX + 160;
    const graphHeight = maxY - minY + 140;

    const scaleX = (this.width || 800) / graphWidth;
    const scaleY = (this.height || 540) / graphHeight;
    this.scale = Math.min(Math.max(Math.min(scaleX, scaleY), 0.6), 1.05);

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    this.panX = (this.width / 2) - centerX * this.scale;
    this.panY = (this.height / 2) - centerY * this.scale;
  }

  applySimulationReport(report) {
    this.simulationState = report;
    this.rippleShockwaves = [];

    this.nodes.forEach(n => {
      n.isAffected = false;
      n.isTarget = false;
      n.hops = 0;
      n.status = 'healthy';
    });
    this.links.forEach(l => l.isBroken = false);

    if (!report) return;

    const targetName = report.target_entity?.toLowerCase() || '';

    let targetNode = null;
    this.nodes.forEach(n => {
      if (n.id.toLowerCase() === targetName || n.name.toLowerCase() === targetName) {
        n.isTarget = true;
        n.status = report.type === 'failure' ? 'offline' : 'upgraded';
        targetNode = n;
      }
    });

    if (report.outage_details && report.outage_details.impacted_services) {
      report.outage_details.impacted_services.forEach(item => {
        const node = this.nodeMap.get(item.id);
        if (node) {
          node.isAffected = true;
          node.hops = item.hops_from_target || 1;
          node.status = item.impact || 'outage';
        }
      });

      if (report.outage_details.broken_endpoints) {
        report.outage_details.broken_endpoints.forEach(ep => {
          const epNode = this.nodeMap.get(ep.id);
          if (epNode) {
            epNode.isAffected = true;
            epNode.status = ep.status || 'broken';
          }
        });
      }

      if (report.outage_details.impacted_clients) {
        report.outage_details.impacted_clients.forEach(c => {
          const cNode = this.nodeMap.get(c.id);
          if (cNode) {
            cNode.isAffected = true;
            cNode.status = 'degraded';
          }
        });
      }

      this.links.forEach(l => {
        if (l.target.isAffected || l.target.isTarget) {
          l.isBroken = true;
        }
      });
    }

    if (targetNode) {
      for (let i = 0; i < 3; i++) {
        setTimeout(() => {
          this.rippleShockwaves.push({
            x: targetNode.x,
            y: targetNode.y,
            radius: 10,
            maxRadius: 360,
            opacity: 0.9,
            color: report.type === 'failure' ? '#f43f5e' : '#38bdf8'
          });
        }, i * 350);
      }
    }
  }

  startLoop() {
    const loop = (t) => {
      this.animTime = t * 0.001;
      this.render();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  render() {
    const dpr = window.devicePixelRatio || 1;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.ctx.clearRect(0, 0, this.width, this.height);

    this.ctx.save();
    this.ctx.translate(this.panX, this.panY);
    this.ctx.scale(this.scale, this.scale);

    // 1. Draw Shockwave Ripples
    this.renderRipples();

    // 2. Draw Links
    this.renderLinks();

    // 3. Draw Nodes
    this.renderNodes();

    this.ctx.restore();

    // 4. Render Tooltip on Screen Space
    if (this.hoveredNode) {
      this.renderTooltip(this.hoveredNode);
    }
  }

  renderRipples() {
    for (let i = this.rippleShockwaves.length - 1; i >= 0; i--) {
      const rip = this.rippleShockwaves[i];
      rip.radius += 2.8;
      rip.opacity = Math.max(0, 0.9 * (1 - rip.radius / rip.maxRadius));

      this.ctx.beginPath();
      this.ctx.arc(rip.x, rip.y, rip.radius, 0, Math.PI * 2);
      this.ctx.strokeStyle = rip.color;
      this.ctx.globalAlpha = rip.opacity;
      this.ctx.lineWidth = 2.5;
      this.ctx.stroke();
      this.ctx.globalAlpha = 1.0;

      if (rip.radius >= rip.maxRadius) {
        this.rippleShockwaves.splice(i, 1);
      }
    }
  }

  renderLinks() {
    const ctx = this.ctx;
    const t = this.animTime;

    this.links.forEach(link => {
      const s = link.source;
      const d = link.target;

      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      const midX = (s.x + d.x) / 2;
      ctx.bezierCurveTo(midX, s.y, midX, d.y, d.x, d.y);

      if (link.isBroken) {
        ctx.strokeStyle = 'rgba(244, 63, 94, 0.5)';
        ctx.lineWidth = 1.8;
        ctx.setLineDash([6, 5]);
      } else {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.lineWidth = 1.2;
        ctx.setLineDash([]);
      }
      ctx.stroke();
      ctx.setLineDash([]);

      if (!link.isBroken) {
        const progress = ((t * link.speed * 0.3) + link.offset) % 1.0;
        const pt = this.getBezierPoint(s.x, s.y, midX, s.y, midX, d.y, d.x, d.y, progress);
        
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = link.type === 'FALLBACK_FOR' ? '#10b981' : 'rgba(56, 189, 248, 0.7)';
        ctx.fill();
      }
    });
  }

  getBezierPoint(p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y, t) {
    const u = 1 - t;
    const tt = t * t;
    const uu = u * u;
    const uuu = uu * u;
    const ttt = tt * t;

    let x = uuu * p0x;
    x += 3 * uu * t * p1x;
    x += 3 * u * tt * p2x;
    x += ttt * p3x;

    let y = uuu * p0y;
    y += 3 * uu * t * p1y;
    y += 3 * u * tt * p2y;
    y += ttt * p3y;

    return { x, y };
  }

  renderNodes() {
    const ctx = this.ctx;
    const t = this.animTime;

    this.nodes.forEach(node => {
      const isHovered = this.hoveredNode === node;
      const isTarget = node.isTarget;
      const isAffected = node.isAffected;

      const breathing = Math.sin(t * 1.5 + node.pulseOffset) * 1.2;
      const r = (node.radius || 20) + (isHovered ? 4 : 0) + (isTarget ? breathing * 1.5 : 0);

      if (isTarget) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 10, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(244, 63, 94, 0.3)';
        ctx.fill();
      } else if (isAffected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 7, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(251, 146, 60, 0.22)';
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      
      let fillColor = '#111827';
      let strokeColor = node.baseColor;

      if (isTarget) {
        fillColor = '#881337';
        strokeColor = '#f43f5e';
      } else if (isAffected) {
        fillColor = '#431407';
        strokeColor = '#fb923c';
      } else if (isHovered) {
        fillColor = '#1e293b';
        strokeColor = '#ffffff';
      }

      ctx.fillStyle = fillColor;
      ctx.fill();
      ctx.lineWidth = isHovered || isTarget ? 2.5 : 1.5;
      ctx.strokeStyle = strokeColor;
      ctx.stroke();

      // Specular glass bevel
      ctx.beginPath();
      ctx.arc(node.x, node.y - r * 0.35, r * 0.45, 0, Math.PI, true);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label text
      ctx.font = '500 11px "Plus Jakarta Sans", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = isHovered ? '#ffffff' : (isTarget ? '#fda4af' : (isAffected ? '#fed7aa' : '#cbd5e1'));
      
      const labelText = node.name || node.id;
      const truncated = labelText.length > 16 ? labelText.slice(0, 14) + '..' : labelText;
      ctx.fillText(truncated, node.x, node.y + r + 5);

      if (node.tier) {
        ctx.font = '600 9px "JetBrains Mono", monospace';
        ctx.fillStyle = node.tier === 1 ? '#38bdf8' : '#94a3b8';
        ctx.fillText(`T${node.tier}`, node.x, node.y - 4);
      }
    });
  }

  renderTooltip(node) {
    const ctx = this.ctx;
    const screenX = node.x * this.scale + this.panX;
    const screenY = node.y * this.scale + this.panY;

    const padding = 12;
    const title = node.name || node.id;
    const sub = `${node.label} ${node.tier ? '• Tier ' + node.tier : ''}`;
    const statusText = `Status: ${node.status.toUpperCase()}`;
    const impactText = node.isTarget ? '🔴 Simulation Target' : (node.isAffected ? `🟠 Affected (+${node.hops} hops)` : '🟢 Operational');

    ctx.font = '600 13px "Plus Jakarta Sans", sans-serif';
    const titleWidth = ctx.measureText(title).width;
    ctx.font = '400 11px "Plus Jakarta Sans", sans-serif';
    const subWidth = ctx.measureText(sub).width;
    const boxWidth = Math.max(titleWidth, subWidth, 140) + padding * 2;
    const boxHeight = 72;

    let tipX = screenX + 28;
    let tipY = screenY - 36;

    if (tipX + boxWidth > this.width - 20) tipX = screenX - boxWidth - 28;
    if (tipY + boxHeight > this.height - 20) tipY = this.height - boxHeight - 20;

    ctx.save();
    ctx.fillStyle = 'rgba(15, 23, 42, 0.94)';
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.18)';
    ctx.lineWidth = 1;
    
    ctx.beginPath();
    ctx.roundRect(tipX, tipY, boxWidth, boxHeight, 8);
    ctx.fill();
    ctx.stroke();

    ctx.font = '600 13px "Plus Jakarta Sans", sans-serif';
    ctx.fillStyle = '#f8fafc';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(title, tipX + padding, tipY + 10);

    ctx.font = '500 11px "Plus Jakarta Sans", sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(sub, tipX + padding, tipY + 28);

    ctx.font = '600 11px "JetBrains Mono", monospace';
    ctx.fillStyle = node.isTarget ? '#f43f5e' : (node.isAffected ? '#fb923c' : '#34d399');
    ctx.fillText(impactText, tipX + padding, tipY + 46);

    ctx.restore();
  }
}

window.GraphVisualizer = GraphVisualizer;

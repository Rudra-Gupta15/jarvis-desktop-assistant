import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function Globe() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const cleanup = initGlobe(canvas);
    return cleanup;
  }, []);

  return (
    <div style={{ width: '100%', height: '100%', background: 'transparent', position: 'relative', overflow: 'hidden' }}>
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
      <div style={{
        position: 'absolute', bottom: '20px', right: '20px',
        color: 'rgba(255,255,255,0.2)', fontSize: '10px',
        fontFamily: 'monospace', pointerEvents: 'none', letterSpacing: '1px',
      }}>
        DRAG TO ROTATE · SCROLL TO ZOOM
      </div>
    </div>
  );
}

function initGlobe(canvas) {
  const container = canvas.parentElement;

  const W = container.offsetWidth || 600;
  const H = container.offsetHeight || 600;
  canvas.width  = W;
  canvas.height = H;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(W, H);
  renderer.setClearColor(0x000000, 0);

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100);
  camera.position.set(0, 0, 4);

  // ── Round dot texture ──────────────────────────────────────────
  const dotCanvas = document.createElement('canvas');
  dotCanvas.width  = 64;
  dotCanvas.height = 64;
  const ctx = dotCanvas.getContext('2d');
  ctx.beginPath();
  ctx.arc(32, 32, 30, 0, Math.PI * 2);
  ctx.fillStyle = '#fff';
  ctx.fill();
  const dotTex = new THREE.CanvasTexture(dotCanvas);

  // ── Globe group ────────────────────────────────────────────────
  const globeGroup = new THREE.Group();
  scene.add(globeGroup);

  // Wireframe sphere
  const wireGeo = new THREE.EdgesGeometry(new THREE.SphereGeometry(1, 48, 48));
  const wireMat = new THREE.LineBasicMaterial({ color: 0x00f2ff, transparent: true, opacity: 0.2 });
  globeGroup.add(new THREE.LineSegments(wireGeo, wireMat));

  // Surface dots
  const dN   = 3000;
  const dPos = new Float32Array(dN * 3);
  for (let i = 0; i < dN; i++) {
    const phi   = Math.acos(-1 + 2 * Math.random());
    const theta = Math.random() * Math.PI * 2;
    dPos[i * 3]     = Math.sin(phi) * Math.cos(theta);
    dPos[i * 3 + 1] = Math.cos(phi);
    dPos[i * 3 + 2] = Math.sin(phi) * Math.sin(theta);
  }
  const dGeo = new THREE.BufferGeometry();
  dGeo.setAttribute('position', new THREE.BufferAttribute(dPos, 3));
  globeGroup.add(new THREE.Points(dGeo, new THREE.PointsMaterial({
    color: 0x00f2ff, size: 0.025, map: dotTex,
    alphaTest: 0.5, transparent: true, opacity: 0.7, sizeAttenuation: true,
  })));

  // Arc particles (animated data streams)
  const aN      = 150;
  const arcData = Array.from({ length: aN }, () => ({
    p1: Math.acos(-1 + 2 * Math.random()), t1: Math.random() * Math.PI * 2,
    p2: Math.acos(-1 + 2 * Math.random()), t2: Math.random() * Math.PI * 2,
    progress: Math.random(),
    speed:  0.002 + Math.random() * 0.005,
    height: 0.2   + Math.random() * 0.4,
  }));
  const aPos = new Float32Array(aN * 3);
  const aGeo = new THREE.BufferGeometry();
  aGeo.setAttribute('position', new THREE.BufferAttribute(aPos, 3));
  globeGroup.add(new THREE.Points(aGeo, new THREE.PointsMaterial({
    color: 0x00f2ff, size: 0.04, map: dotTex,
    alphaTest: 0.5, transparent: true, opacity: 0.9, sizeAttenuation: true,
  })));

  // Outer glow shell
  globeGroup.add(new THREE.Mesh(
    new THREE.SphereGeometry(1.12, 32, 32),
    new THREE.MeshBasicMaterial({ color: 0x00f2ff, transparent: true, opacity: 0.04, side: THREE.BackSide }),
  ));

  // ── Arc interpolation ──────────────────────────────────────────
  function arcPosition(p1, t1, p2, t2, h, p) {
    const x1 = Math.sin(p1)*Math.cos(t1), y1 = Math.cos(p1), z1 = Math.sin(p1)*Math.sin(t1);
    const x2 = Math.sin(p2)*Math.cos(t2), y2 = Math.cos(p2), z2 = Math.sin(p2)*Math.sin(t2);
    const mx = (x1+x2)/2*(1+h), my = (y1+y2)/2*(1+h), mz = (z1+z2)/2*(1+h);
    let ax, ay, az;
    if (p < 0.5) {
      ax = x1+(mx-x1)*p*2; ay = y1+(my-y1)*p*2; az = z1+(mz-z1)*p*2;
    } else {
      ax = mx+(x2-mx)*(p*2-1); ay = my+(y2-my)*(p*2-1); az = mz+(z2-mz)*(p*2-1);
    }
    const l = Math.sqrt(ax*ax+ay*ay+az*az) || 1;
    return [ax/l, ay/l, az/l];
  }

  // ── Mouse / Touch drag ─────────────────────────────────────────
  let isDragging = false, lastX = 0, lastY = 0, rotY = 0, rotX = 0, velX = 0, velY = 0;

  const onMouseDown = e => { isDragging = true; lastX = e.clientX; lastY = e.clientY; velX = velY = 0; };
  const onMouseMove = e => {
    if (!isDragging) return;
    velX = (e.clientX - lastX) * 0.005;
    velY = (e.clientY - lastY) * 0.005;
    rotY += velX; rotX += velY;
    lastX = e.clientX; lastY = e.clientY;
  };
  const onMouseUp = () => isDragging = false;

  const onWheel = e => {
    e.preventDefault();
    camera.position.z = Math.max(2.5, Math.min(8.0, camera.position.z + e.deltaY * 0.005));
  };

  canvas.addEventListener('mousedown', onMouseDown);
  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
  canvas.addEventListener('wheel', onWheel, { passive: false });

  // ── Resize ─────────────────────────────────────────────────────
  const onResize = () => {
    const W = container.offsetWidth, H = container.offsetHeight;
    if (!W || !H) return;
    canvas.width = W; canvas.height = H;
    renderer.setSize(W, H);
    camera.aspect = W / H;
    camera.updateProjectionMatrix();
  };
  window.addEventListener('resize', onResize);

  // ── Animation loop ─────────────────────────────────────────────
  let animId;
  function loop() {
    animId = requestAnimationFrame(loop);
    if (!isDragging) {
      velX *= 0.95; velY *= 0.95;
      rotY += velX + 0.002;
      rotX += velY;
    }
    rotX = Math.max(-0.8, Math.min(0.8, rotX));
    globeGroup.rotation.set(rotX, rotY, 0);

    arcData.forEach((a, i) => {
      a.progress += a.speed;
      if (a.progress > 1) a.progress = 0;
      const [x, y, z] = arcPosition(a.p1, a.t1, a.p2, a.t2, a.height, a.progress);
      aPos[i*3] = x; aPos[i*3+1] = y; aPos[i*3+2] = z;
    });
    aGeo.attributes.position.needsUpdate = true;

    renderer.render(scene, camera);
  }
  loop();

  // ── Cleanup ────────────────────────────────────────────────────
  return () => {
    cancelAnimationFrame(animId);
    canvas.removeEventListener('mousedown', onMouseDown);
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
    canvas.removeEventListener('wheel', onWheel);
    window.removeEventListener('resize', onResize);
    renderer.dispose();
    dotTex.dispose();
    dGeo.dispose();
    aGeo.dispose();
  };
}

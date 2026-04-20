/* canvas.js — Annotation canvas engine */
const Canvas = (() => {
  let canvas, ctx, wrapper;
  let img = null;
  let scale = 1, offsetX = 0, offsetY = 0;
  let tool = 'bbox';
  let isDrawing = false;
  let startX, startY;
  let currentAnnotations = [];  // { id, type, label, color, coords, geometry }
  let selectedAnn = null;
  let panStart = null;
  let activeLabel = { name: 'unlabeled', color: '#00c2ff' };
  let onAnnotationsChange = null;

  // Polygon in-progress
  let polyPoints = [];

  function init(canvasEl, wrapperEl, onChange) {
    canvas = canvasEl;
    ctx = canvas.getContext('2d');
    wrapper = wrapperEl;
    onAnnotationsChange = onChange;
    bindEvents();
  }

  function setTool(t) { tool = t; isDrawing = false; polyPoints = []; redraw(); }
  function setActiveLabel(label) { activeLabel = label; }

  function loadImage(src) {
    return new Promise((resolve) => {
      const image = new Image();
      image.crossOrigin = 'anonymous';
      image.onload = () => {
        img = image;
        fitToWrapper();
        canvas.style.display = 'block';
        document.getElementById('canvas-placeholder').style.display = 'none';
        redraw();
        resolve();
      };
      image.onerror = () => {
        // Draw a placeholder grid for non-renderable files (NetCDF etc.)
        img = null;
        canvas.style.display = 'block';
        document.getElementById('canvas-placeholder').style.display = 'none';
        fitToWrapper();
        redraw();
        resolve();
      };
      image.src = src;
    });
  }

  function fitToWrapper() {
    const ww = wrapper.clientWidth;
    const wh = wrapper.clientHeight;
    canvas.width  = ww;
    canvas.height = wh;

    if (img) {
      scale = Math.min(ww / img.width, wh / img.height) * 0.92;
      offsetX = (ww - img.width  * scale) / 2;
      offsetY = (wh - img.height * scale) / 2;
    } else {
      scale = 1; offsetX = 0; offsetY = 0;
    }
  }

  function redraw() {
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (img) {
      ctx.drawImage(img, offsetX, offsetY, img.width * scale, img.height * scale);
    } else {
      // Placeholder grid for scientific data
      ctx.fillStyle = '#0e1620';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = '#1e3047';
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
      }
      ctx.fillStyle = '#3d5e7a'; ctx.font = '14px "Space Mono"';
      ctx.textAlign = 'center';
      ctx.fillText('Scientific data — annotations active', canvas.width/2, canvas.height/2);
    }

    // Draw all annotations
    currentAnnotations.forEach(ann => drawAnnotation(ann, ann === selectedAnn));

    // Draw in-progress polygon
    if (tool === 'polygon' && polyPoints.length > 0) {
      ctx.strokeStyle = activeLabel.color;
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      polyPoints.forEach((p, i) => i === 0 ? ctx.moveTo(p[0], p[1]) : ctx.lineTo(p[0], p[1]));
      ctx.stroke();
      ctx.setLineDash([]);
      polyPoints.forEach(p => {
        ctx.fillStyle = activeLabel.color;
        ctx.beginPath(); ctx.arc(p[0], p[1], 4, 0, Math.PI*2); ctx.fill();
      });
    }
  }

  function drawAnnotation(ann, selected = false) {
    ctx.strokeStyle = ann.color || '#00c2ff';
    ctx.lineWidth = selected ? 2.5 : 1.5;
    ctx.fillStyle = hexToRgba(ann.color || '#00c2ff', selected ? 0.25 : 0.12);

    if (ann.type === 'bbox' && ann.coords) {
      const [x1, y1, x2, y2] = ann.coords;
      const sx = x1*scale+offsetX, sy = y1*scale+offsetY;
      const sw = (x2-x1)*scale,   sh = (y2-y1)*scale;
      ctx.beginPath(); ctx.rect(sx, sy, sw, sh);
      ctx.fill(); ctx.stroke();

      // Label tag
      ctx.fillStyle = ann.color || '#00c2ff';
      const tag = ann.label;
      ctx.font = '11px "DM Sans"';
      const tw = ctx.measureText(tag).width + 8;
      ctx.fillRect(sx, sy - 18, tw, 18);
      ctx.fillStyle = '#080d14';
      ctx.fillText(tag, sx + 4, sy - 5);

    } else if (ann.type === 'polygon' && ann.coords && ann.coords.length > 1) {
      ctx.beginPath();
      ann.coords.forEach(([x, y], i) => {
        const sx = x*scale+offsetX, sy = y*scale+offsetY;
        i === 0 ? ctx.moveTo(sx, sy) : ctx.lineTo(sx, sy);
      });
      ctx.closePath(); ctx.fill(); ctx.stroke();

    } else if (ann.type === 'point' && ann.coords) {
      const [x, y] = ann.coords;
      const sx = x*scale+offsetX, sy = y*scale+offsetY;
      ctx.beginPath(); ctx.arc(sx, sy, 7, 0, Math.PI*2);
      ctx.fill(); ctx.stroke();
    }
  }

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function canvasToImage(cx, cy) {
    return [(cx - offsetX) / scale, (cy - offsetY) / scale];
  }

  function bindEvents() {
    canvas.addEventListener('mousedown', onMouseDown);
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('mouseup',   onMouseUp);
    canvas.addEventListener('dblclick',  onDblClick);
    canvas.addEventListener('wheel', e => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.1 : 0.9;
      const cx = e.offsetX, cy = e.offsetY;
      offsetX = cx - (cx - offsetX) * factor;
      offsetY = cy - (cy - offsetY) * factor;
      scale *= factor;
      redraw();
    }, { passive: false });
  }

  function onMouseDown(e) {
    const { offsetX: cx, offsetY: cy } = e;
    if (tool === 'pan') { panStart = { cx, cy, ox: offsetX, oy: offsetY }; return; }
    if (tool === 'polygon') {
      const [ix, iy] = canvasToImage(cx, cy);
      polyPoints.push([ix, iy]); redraw(); return;
    }
    isDrawing = true;
    [startX, startY] = canvasToImage(cx, cy);
  }

  function onMouseMove(e) {
    if (panStart) {
      offsetX = panStart.ox + (e.offsetX - panStart.cx);
      offsetY = panStart.oy + (e.offsetY - panStart.cy);
      redraw(); return;
    }
    if (!isDrawing) return;
    redraw();
    const [curX, curY] = canvasToImage(e.offsetX, e.offsetY);

    if (tool === 'bbox') {
      ctx.strokeStyle = activeLabel.color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 3]);
      const sx = startX*scale+offsetX, sy = startY*scale+offsetY;
      ctx.strokeRect(sx, sy, (curX-startX)*scale, (curY-startY)*scale);
      ctx.setLineDash([]);
    }
  }

  function onMouseUp(e) {
    if (panStart) { panStart = null; return; }
    if (!isDrawing) return;
    isDrawing = false;
    const [endX, endY] = canvasToImage(e.offsetX, e.offsetY);

    if (tool === 'bbox') {
      const x1 = Math.min(startX, endX), y1 = Math.min(startY, endY);
      const x2 = Math.max(startX, endX), y2 = Math.max(startY, endY);
      if (x2 - x1 < 5 || y2 - y1 < 5) return;

      const ann = {
        id: Date.now(), type: 'bbox', label: activeLabel.name,
        color: activeLabel.color, coords: [x1, y1, x2, y2],
        geometry: { type: 'bbox', coordinates: [x1, y1, x2, y2] },
      };
      currentAnnotations.push(ann);
      selectedAnn = ann;
      redraw();
      onAnnotationsChange && onAnnotationsChange(currentAnnotations);

    } else if (tool === 'point') {
      const ann = {
        id: Date.now(), type: 'point', label: activeLabel.name,
        color: activeLabel.color, coords: [endX, endY],
        geometry: { type: 'Point', coordinates: [endX, endY] },
      };
      currentAnnotations.push(ann);
      selectedAnn = ann;
      redraw();
      onAnnotationsChange && onAnnotationsChange(currentAnnotations);
    }
  }

  function onDblClick() {
    if (tool === 'polygon' && polyPoints.length >= 3) {
      const ann = {
        id: Date.now(), type: 'polygon', label: activeLabel.name,
        color: activeLabel.color, coords: [...polyPoints],
        geometry: { type: 'Polygon', coordinates: [polyPoints.map(([x,y]) => [x, y])] },
      };
      currentAnnotations.push(ann);
      selectedAnn = ann;
      polyPoints = [];
      redraw();
      onAnnotationsChange && onAnnotationsChange(currentAnnotations);
    }
  }

  function setAnnotations(anns) {
    currentAnnotations = anns.map(a => {
      const geo = a.geometry || {};
      let coords = null, type = a.annotation_type;

      if (type === 'bbox' && geo.coordinates)        coords = geo.coordinates;
      else if (type === 'polygon' && geo.coordinates) coords = geo.coordinates[0];
      else if (type === 'point' && geo.coordinates)   coords = geo.coordinates;

      return {
        id: a.id, _serverId: a.id, type, label: a.label,
        color: '#00c2ff', coords, geometry: geo,
        confidence: a.confidence, status: a.status,
      };
    });
    selectedAnn = null;
    redraw();
  }

  function clearAnnotations() { currentAnnotations = []; selectedAnn = null; polyPoints = []; redraw(); }

  function selectAnnotation(id) {
    selectedAnn = currentAnnotations.find(a => a.id === id) || null;
    redraw();
  }

  function removeAnnotation(id) {
    currentAnnotations = currentAnnotations.filter(a => a.id !== id);
    if (selectedAnn && selectedAnn.id === id) selectedAnn = null;
    redraw();
    onAnnotationsChange && onAnnotationsChange(currentAnnotations);
  }

  function getAnnotations() { return currentAnnotations; }

  return {
    init, setTool, setActiveLabel, loadImage, fitToWrapper,
    setAnnotations, clearAnnotations, selectAnnotation, removeAnnotation, getAnnotations,
    redraw,
  };
})();

window.Canvas = Canvas;

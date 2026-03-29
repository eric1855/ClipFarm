// Terminal Window Drag — makes .terminal-window draggable by its titlebar

document.addEventListener('DOMContentLoaded', () => {
  const win = document.querySelector('.terminal-window');
  const titlebar = document.querySelector('.terminal-titlebar');
  if (!win || !titlebar) return;

  let isDragging = false;
  let dragStartX, dragStartY, winStartX, winStartY;

  // Compute initial centered position and switch from CSS transform to pixel coords
  const initX = (window.innerWidth - win.offsetWidth) / 2;
  const initY = 20;
  win.style.left = initX + 'px';
  win.style.top = initY + 'px';
  win.classList.add('drag-initialized');

  function getClientPos(e) {
    if (e.touches && e.touches.length) return { x: e.touches[0].clientX, y: e.touches[0].clientY };
    return { x: e.clientX, y: e.clientY };
  }

  function isInteractive(el) {
    return el.closest('button, a, input, select, textarea, label, [role="button"]');
  }

  function startDrag(e) {
    if (isInteractive(e.target)) return;
    e.preventDefault();
    isDragging = true;
    const pos = getClientPos(e);
    dragStartX = pos.x;
    dragStartY = pos.y;
    winStartX = win.offsetLeft;
    winStartY = win.offsetTop;
    win.classList.add('dragging');
    win.classList.remove('snap-back');
  }

  function onDrag(e) {
    if (!isDragging) return;
    e.preventDefault();
    const pos = getClientPos(e);
    let newLeft = winStartX + (pos.x - dragStartX);
    let newTop = winStartY + (pos.y - dragStartY);

    // Clamp to viewport
    newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - win.offsetWidth));
    newTop = Math.max(0, Math.min(newTop, window.innerHeight - win.offsetHeight));

    win.style.left = newLeft + 'px';
    win.style.top = newTop + 'px';
  }

  function stopDrag() {
    if (!isDragging) return;
    isDragging = false;
    win.classList.remove('dragging');
  }

  function snapToCenter() {
    win.classList.add('snap-back');
    win.style.left = ((window.innerWidth - win.offsetWidth) / 2) + 'px';
    win.style.top = '20px';
    setTimeout(() => win.classList.remove('snap-back'), 350);
  }

  // Mouse events
  titlebar.addEventListener('mousedown', startDrag);
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);

  // Touch events
  titlebar.addEventListener('touchstart', startDrag, { passive: false });
  document.addEventListener('touchmove', onDrag, { passive: false });
  document.addEventListener('touchend', stopDrag);
  document.addEventListener('touchcancel', stopDrag);

  // Double-click to re-center
  titlebar.addEventListener('dblclick', (e) => {
    if (isInteractive(e.target)) return;
    snapToCenter();
  });

  // Keep window in bounds on resize
  window.addEventListener('resize', () => {
    let left = win.offsetLeft;
    let top = win.offsetTop;
    left = Math.max(0, Math.min(left, window.innerWidth - win.offsetWidth));
    top = Math.max(0, Math.min(top, window.innerHeight - win.offsetHeight));
    win.style.left = left + 'px';
    win.style.top = top + 'px';
  });
});

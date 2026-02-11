const state = {
  planets: [],
  goods: [],
  market: [],
  routes: [],
  lanes: [],
  selectedPlanetId: null,
  bounds: { minX: 0, maxX: 1, minY: 0, maxY: 1 },
  viewport: { width: 1, height: 1 },
  view: {
    zoom: 1,
    offsetX: 0,
    offsetY: 0,
    minZoom: 0.35,
    maxZoom: 3,
    initialized: false,
  },
  interaction: {
    dragging: false,
    lastX: 0,
    lastY: 0,
    velocityX: 0,
    velocityY: 0,
    lastTime: 0,
    moved: false,
    suppressClick: false,
    inertiaId: null,
  },
};

const planetListEl = document.getElementById("planetList");
const marketListEl = document.getElementById("marketList");
const routesListEl = document.getElementById("routesList");
const marketTitleEl = document.getElementById("marketTitle");
const playerStatusEl = document.getElementById("playerStatus");
const planetSearchEl = document.getElementById("planetSearch");
const canvas = document.getElementById("mapCanvas");
const ctx = canvas.getContext("2d");
const zoomInBtn = document.getElementById("zoomIn");
const zoomOutBtn = document.getElementById("zoomOut");
const zoomResetBtn = document.getElementById("zoomReset");

const typeColors = {
  Earthlike: "#6fe3a5",
  "Gas Giant": "#5cc8ff",
  Lava: "#ff7b5c",
  Rock: "#c4b6a2",
  Barren: "#a58a6f",
  Ice: "#9cc7ff",
  Ocean: "#5e9dff",
  Jungle: "#6de07f",
  Desert: "#f0c36b",
  Tundra: "#a6b6c9",
  Metallic: "#b0c2d8",
};

const api = {
  planets: () => fetch("/api/planets").then((res) => res.json()),
  goods: () => fetch("/api/goods").then((res) => res.json()),
  market: (id) => fetch(`/api/planets/${id}/market`).then((res) => res.json()),
  routes: (id) => fetch(`/api/routes?planet_id=${id}`).then((res) => res.json()),
  lanes: () => fetch("/api/lanes").then((res) => res.json()),
  player: () => fetch("/api/player").then((res) => res.json()),
};

function setBounds(planets) {
  const xs = planets.map((p) => p.x);
  const ys = planets.map((p) => p.y);
  state.bounds = {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function worldToScreen(x, y) {
  return {
    x: x * state.view.zoom + state.view.offsetX,
    y: y * state.view.zoom + state.view.offsetY,
  };
}

function screenToWorld(x, y) {
  return {
    x: (x - state.view.offsetX) / state.view.zoom,
    y: (y - state.view.offsetY) / state.view.zoom,
  };
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function fitViewToBounds() {
  const padding = 60;
  const width = state.viewport.width;
  const height = state.viewport.height;
  const spanX = state.bounds.maxX - state.bounds.minX || 1;
  const spanY = state.bounds.maxY - state.bounds.minY || 1;
  const zoomX = (width - padding * 2) / spanX;
  const zoomY = (height - padding * 2) / spanY;
  state.view.zoom = clamp(Math.min(zoomX, zoomY), state.view.minZoom, state.view.maxZoom);
  state.view.offsetX = padding - state.bounds.minX * state.view.zoom;
  state.view.offsetY = padding - state.bounds.minY * state.view.zoom;
  state.view.initialized = true;
}

function applyZoom(nextZoom, screenX, screenY) {
  const world = screenToWorld(screenX, screenY);
  state.view.zoom = nextZoom;
  state.view.offsetX = screenX - world.x * nextZoom;
  state.view.offsetY = screenY - world.y * nextZoom;
}

function zoomAt(screenX, screenY, factor) {
  const nextZoom = clamp(
    state.view.zoom * factor,
    state.view.minZoom,
    state.view.maxZoom,
  );
  applyZoom(nextZoom, screenX, screenY);
  drawMap();
}

function drawGrid() {
  const spacing = 100;
  const majorEvery = 5;
  const topLeft = screenToWorld(0, 0);
  const bottomRight = screenToWorld(state.viewport.width, state.viewport.height);

  const startX = Math.floor(topLeft.x / spacing) * spacing;
  const endX = Math.ceil(bottomRight.x / spacing) * spacing;
  const startY = Math.floor(topLeft.y / spacing) * spacing;
  const endY = Math.ceil(bottomRight.y / spacing) * spacing;

  ctx.save();
  ctx.font = "11px Space Grotesk";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";

  for (let x = startX; x <= endX; x += spacing) {
    const screen = worldToScreen(x, 0).x;
    const isMajor = (Math.round(x / spacing) % majorEvery) === 0;
    ctx.strokeStyle = isMajor ? "rgba(92,200,255,0.12)" : "rgba(92,200,255,0.06)";
    ctx.lineWidth = isMajor ? 1.4 : 1;
    ctx.beginPath();
    ctx.moveTo(screen, 0);
    ctx.lineTo(screen, state.viewport.height);
    ctx.stroke();
    if (isMajor) {
      const label = `X ${Math.round(x)}`;
      ctx.fillStyle = "rgba(9,13,20,0.6)";
      ctx.fillRect(screen + 4, 6, ctx.measureText(label).width + 8, 16);
      ctx.fillStyle = "rgba(230,238,248,0.65)";
      ctx.fillText(label, screen + 8, 8);
    }
  }

  for (let y = startY; y <= endY; y += spacing) {
    const screen = worldToScreen(0, y).y;
    const isMajor = (Math.round(y / spacing) % majorEvery) === 0;
    ctx.strokeStyle = isMajor ? "rgba(92,200,255,0.12)" : "rgba(92,200,255,0.06)";
    ctx.lineWidth = isMajor ? 1.4 : 1;
    ctx.beginPath();
    ctx.moveTo(0, screen);
    ctx.lineTo(state.viewport.width, screen);
    ctx.stroke();
    if (isMajor) {
      const label = `Y ${Math.round(y)}`;
      ctx.fillStyle = "rgba(9,13,20,0.6)";
      ctx.fillRect(6, screen + 4, ctx.measureText(label).width + 8, 16);
      ctx.fillStyle = "rgba(230,238,248,0.65)";
      ctx.fillText(label, 10, screen + 6);
    }
  }

  ctx.restore();
}

function drawMap() {
  ctx.clearRect(0, 0, state.viewport.width, state.viewport.height);
  drawGrid();

  state.lanes.forEach((lane) => {
    const from = worldToScreen(lane.ax, lane.ay);
    const to = worldToScreen(lane.bx, lane.by);
    const isSelected =
      lane.planet_a === state.selectedPlanetId ||
      lane.planet_b === state.selectedPlanetId;
    ctx.strokeStyle = isSelected
      ? "rgba(240,165,70,0.85)"
      : "rgba(92,200,255,0.18)";
    ctx.lineWidth = isSelected ? 2 : 1;
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
  });

  state.planets.forEach((planet) => {
    const point = worldToScreen(planet.x, planet.y);
    const color = typeColors[planet.type] || "#e6eef8";
    const isSelected = planet.id === state.selectedPlanetId;
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.arc(point.x, point.y, isSelected ? 7 : 4.5, 0, Math.PI * 2);
    ctx.fill();
    if (isSelected) {
      ctx.strokeStyle = "rgba(240,165,70,0.9)";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  });
}

function renderPlanets(list) {
  planetListEl.innerHTML = "";
  list.forEach((planet) => {
    const card = document.createElement("div");
    card.className = "planet-card" + (planet.id === state.selectedPlanetId ? " active" : "");
    card.innerHTML = `
      <h4>${planet.name}</h4>
      <span>${planet.type} · ${planet.temperature} · Pop ${formatNumber(planet.population)}</span>
    `;
    card.addEventListener("click", () => selectPlanet(planet.id));
    planetListEl.appendChild(card);
  });
}

function renderMarket() {
  marketListEl.innerHTML = "";
  if (!state.market.length) {
    marketListEl.innerHTML = "<p class=\"muted\">No market data.</p>";
    return;
  }

  state.market.forEach((item) => {
    const row = document.createElement("div");
    row.className = "market-item";
    row.innerHTML = `
      <strong>${item.name}</strong>
      <span>${item.price} cr</span>
      <span>S ${item.supply} / D ${item.demand}</span>
    `;
    marketListEl.appendChild(row);
  });
}

function renderRoutes() {
  routesListEl.innerHTML = "";
  if (!state.routes.length) {
    routesListEl.innerHTML = "<p class=\"muted\">No profitable routes.</p>";
    return;
  }

  state.routes.forEach((route) => {
    const row = document.createElement("div");
    row.className = "route-item";
    row.innerHTML = `
      <div>
        <strong>${route.good}</strong>
        <span>${route.from_name} → ${route.to_name}</span>
      </div>
      <div>
        <strong>+${route.profit_per_unit} cr</strong>
        <span>${route.distance} ly</span>
      </div>
    `;
    routesListEl.appendChild(row);
  });
}

function formatNumber(value) {
  return value.toLocaleString("en-US");
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  state.viewport = { width: rect.width, height: rect.height };
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
  if (!state.view.initialized && state.planets.length) {
    fitViewToBounds();
  }
  drawMap();
}

function stopInertia() {
  if (state.interaction.inertiaId) {
    cancelAnimationFrame(state.interaction.inertiaId);
    state.interaction.inertiaId = null;
  }
}

function startInertia() {
  stopInertia();
  const friction = 0.92;
  const minSpeed = 0.15;

  const step = () => {
    state.view.offsetX += state.interaction.velocityX;
    state.view.offsetY += state.interaction.velocityY;
    state.interaction.velocityX *= friction;
    state.interaction.velocityY *= friction;
    drawMap();

    if (
      Math.abs(state.interaction.velocityX) < minSpeed &&
      Math.abs(state.interaction.velocityY) < minSpeed
    ) {
      state.interaction.inertiaId = null;
      return;
    }
    state.interaction.inertiaId = requestAnimationFrame(step);
  };

  state.interaction.inertiaId = requestAnimationFrame(step);
}

async function selectPlanet(id) {
  state.selectedPlanetId = id;
  const planet = state.planets.find((item) => item.id === id);
  if (planet) {
    marketTitleEl.textContent = `${planet.name} Market`;
  }
  state.market = await api.market(id);
  state.routes = await api.routes(id);
  renderPlanets(filterPlanets(planetSearchEl.value));
  renderMarket();
  renderRoutes();
  drawMap();
}

function filterPlanets(term) {
  const lowered = term.toLowerCase();
  return state.planets.filter((planet) =>
    planet.name.toLowerCase().includes(lowered)
  );
}

async function load() {
  const [planets, goods, player, lanes] = await Promise.all([
    api.planets(),
    api.goods(),
    api.player(),
    api.lanes(),
  ]);
  state.planets = planets;
  state.goods = goods;
  state.lanes = lanes;
  playerStatusEl.textContent = `${player.credits} credits · ${player.fleet.length} ships`;
  setBounds(planets);
  renderPlanets(planets);
  fitViewToBounds();
  resizeCanvas();
  if (planets.length) {
    selectPlanet(planets[0].id);
  }
}

planetSearchEl.addEventListener("input", (event) => {
  renderPlanets(filterPlanets(event.target.value));
});

canvas.addEventListener("click", (event) => {
  if (state.interaction.suppressClick) {
    state.interaction.suppressClick = false;
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  let closest = null;
  let bestDistance = Infinity;

  state.planets.forEach((planet) => {
    const point = worldToScreen(planet.x, planet.y);
    const distance = Math.hypot(point.x - x, point.y - y);
    if (distance < 14 && distance < bestDistance) {
      bestDistance = distance;
      closest = planet;
    }
  });

  if (closest) {
    selectPlanet(closest.id);
  }
});

canvas.addEventListener("mousedown", (event) => {
  stopInertia();
  state.interaction.dragging = true;
  state.interaction.lastX = event.clientX;
  state.interaction.lastY = event.clientY;
  state.interaction.velocityX = 0;
  state.interaction.velocityY = 0;
  state.interaction.lastTime = performance.now();
  state.interaction.moved = false;
  canvas.classList.add("dragging");
});

window.addEventListener("mouseup", () => {
  if (!state.interaction.dragging) {
    return;
  }
  state.interaction.dragging = false;
  canvas.classList.remove("dragging");
  if (state.interaction.moved) {
    state.interaction.suppressClick = true;
  }
  const speed = Math.hypot(state.interaction.velocityX, state.interaction.velocityY);
  if (speed > 0.2) {
    startInertia();
  }
});

window.addEventListener("mousemove", (event) => {
  if (!state.interaction.dragging) {
    return;
  }
  const dx = event.clientX - state.interaction.lastX;
  const dy = event.clientY - state.interaction.lastY;
  const now = performance.now();
  const dt = Math.max(8, now - state.interaction.lastTime);
  state.interaction.lastX = event.clientX;
  state.interaction.lastY = event.clientY;
  state.interaction.lastTime = now;
  state.view.offsetX += dx;
  state.view.offsetY += dy;
  state.interaction.velocityX = (dx / dt) * 16;
  state.interaction.velocityY = (dy / dt) * 16;
  if (Math.abs(dx) + Math.abs(dy) > 1) {
    state.interaction.moved = true;
  }
  drawMap();
});

canvas.addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const zoomFactor = 1 - event.deltaY * 0.0015;
    zoomAt(x, y, zoomFactor);
  },
  { passive: false },
);

zoomInBtn.addEventListener("click", () => {
  zoomAt(state.viewport.width / 2, state.viewport.height / 2, 1.15);
});

zoomOutBtn.addEventListener("click", () => {
  zoomAt(state.viewport.width / 2, state.viewport.height / 2, 0.85);
});

zoomResetBtn.addEventListener("click", () => {
  fitViewToBounds();
  drawMap();
});

window.addEventListener("resize", () => {
  resizeCanvas();
});

load();

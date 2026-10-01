/**
 * DAIC Archive - Knowledge Graph Controller
 * Renders an interactive SVG node-link network with linked archival metadata.
 */

let graphData = { nodes: [], edges: [] };
let selectedNode = null;

document.addEventListener('DOMContentLoaded', () => {
  loadKnowledgeGraph();
});

async function loadKnowledgeGraph() {
  const svg = document.getElementById('knowledge-svg');
  if (!svg) return;

  try {
    const data = await api.getKnowledge();
    graphData = data;
    renderSVGGraph(data);
    // Select Ambedkar by default
    const ambedkarNode = data.nodes.find(n => n.id === 'ENT_AMBEDKAR');
    if (ambedkarNode) selectNode(ambedkarNode);
  } catch (e) {
    console.error("Failed to load knowledge graph:", e);
  }
}

function renderSVGGraph(data) {
  const svg = document.getElementById('knowledge-svg');
  if (!svg) return;

  const width = svg.clientWidth || 800;
  const height = svg.clientHeight || 650;
  const centerX = width / 2;
  const centerY = height / 2;

  // Clear previous SVG contents
  svg.innerHTML = `
    <defs>
      <marker id="arrow" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#C2B69D" />
      </marker>
    </defs>
    <g id="graph-group"></g>
  `;

  const group = document.getElementById('graph-group');

  // Compute node coordinates radially around center node
  const nodes = data.nodes || [];
  const edges = data.edges || [];

  const nodePositions = {};
  const radius = Math.min(width, height) * 0.38;

  nodes.forEach((n, idx) => {
    if (n.id === 'ENT_AMBEDKAR') {
      nodePositions[n.id] = { x: centerX, y: centerY, node: n };
    } else {
      const angle = (idx / (nodes.length - 1)) * 2 * Math.PI;
      nodePositions[n.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        node: n
      };
    }
  });

  // 1. Draw Edges
  edges.forEach(edge => {
    const s = nodePositions[edge.source_id];
    const t = nodePositions[edge.target_id];
    if (s && t) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', s.x);
      line.setAttribute('y1', s.y);
      line.setAttribute('x2', t.x);
      line.setAttribute('y2', t.y);
      line.setAttribute('stroke', '#D5CAB6');
      line.setAttribute('stroke-width', '1.5');
      line.setAttribute('marker-end', 'url(#arrow)');
      group.appendChild(line);

      // Edge Label
      const midX = (s.x + t.x) / 2;
      const midY = (s.y + t.y) / 2;
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', midX);
      text.setAttribute('y', midY - 3);
      text.setAttribute('font-size', '9');
      text.setAttribute('fill', '#8A7D68');
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('class', 'select-none pointer-events-none');
      text.textContent = edge.relation;
      group.appendChild(text);
    }
  });

  // 2. Draw Nodes
  nodes.forEach(n => {
    const pos = nodePositions[n.id];
    if (!pos) return;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);
    g.setAttribute('class', 'cursor-pointer group');
    g.addEventListener('click', () => selectNode(n));

    // Outer circle
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    const isCentral = n.id === 'ENT_AMBEDKAR';
    circle.setAttribute('r', isCentral ? '24' : '16');
    circle.setAttribute('fill', getNodeColor(n.category));
    circle.setAttribute('stroke', isCentral ? '#D7A940' : '#FFFFFF');
    circle.setAttribute('stroke-width', isCentral ? '3' : '2');
    circle.setAttribute('class', 'transition-all duration-200 group-hover:scale-125 shadow-md');
    circle.setAttribute('id', `circle-${n.id}`);

    // Text Label below
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('y', isCentral ? '36' : '28');
    text.setAttribute('font-size', isCentral ? '11' : '10');
    text.setAttribute('font-weight', isCentral ? 'bold' : '500');
    text.setAttribute('fill', '#141F39');
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('class', 'select-none');
    text.textContent = n.label;

    g.appendChild(circle);
    g.appendChild(text);
    group.appendChild(g);
  });
}

function getNodeColor(category) {
  switch (category) {
    case 'Person': return '#141F39';
    case 'Idea': return '#3B7558';
    case 'Document': return '#B88B28';
    case 'Event': return '#8C5B08';
    case 'Institution': return '#4A5568';
    case 'Place': return '#6B7280';
    default: return '#141F39';
  }
}

function selectNode(node) {
  selectedNode = node;
  const title = document.getElementById('dossier-title');
  const catBadge = document.getElementById('dossier-category-badge');
  const desc = document.getElementById('dossier-desc');
  const relList = document.getElementById('dossier-relations-list');
  const askBtn = document.getElementById('dossier-ask-btn');

  if (title) title.textContent = node.label;
  if (catBadge) {
    catBadge.textContent = node.category;
    catBadge.style.backgroundColor = getNodeColor(node.category);
    catBadge.style.color = '#FFFFFF';
  }
  if (desc) desc.textContent = node.description || "Archival entity in the Ambedkar knowledge corpus.";

  // Find connected relations
  const connected = (graphData.edges || []).filter(e => e.source_id === node.id || e.target_id === node.id);

  if (relList) {
    if (connected.length === 0) {
      relList.innerHTML = `<p class="text-gray-400 italic">No direct connections mapped.</p>`;
    } else {
      relList.innerHTML = connected.map(e => {
        const isSource = e.source_id === node.id;
        const otherId = isSource ? e.target_id : e.source_id;
        const otherNode = (graphData.nodes || []).find(n => n.id === otherId);
        const otherLabel = otherNode ? otherNode.label : otherId;

        return `
          <div class="p-2 rounded bg-gray-50 border border-gray-200">
            <div class="font-bold text-[#141F39] text-xs">${isSource ? `→ ${e.relation}` : `← ${e.relation} by`}</div>
            <div class="text-[#8C5B08] font-medium mt-0.5">${otherLabel}</div>
            <div class="text-[10px] text-gray-500 mt-1">${e.description || ''}</div>
            ${e.citation_id ? `
              <button onclick="DAIC.openOriginalDocument('${e.citation_id}')" class="text-[10px] text-[#B88B28] font-bold hover:underline mt-1 block">
                Inspect Source Document (${e.citation_id}) →
              </button>
            ` : ''}
          </div>
        `;
      }).join('');
    }
  }

  if (askBtn) {
    askBtn.onclick = () => {
      window.location.href = `/ask?q=Tell%20me%20about%20${encodeURIComponent(node.label)}%20and%20its%20significance%20in%20Ambedkar's%20work`;
    };
  }
}

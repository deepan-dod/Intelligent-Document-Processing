// IDIS Client-Side Interactivity & UI Utilities

document.addEventListener('DOMContentLoaded', () => {
  // 1. Toast dismissal
  document.querySelectorAll('.flash-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const flash = btn.closest('.flash');
      if (flash) flash.remove();
    });
  });

  // Auto-dismiss success flash messages after 6 seconds
  setTimeout(() => {
    document.querySelectorAll('.flash.success').forEach(f => {
      f.style.opacity = '0';
      f.style.transition = 'opacity 0.5s ease';
      setTimeout(() => f.remove(), 500);
    });
  }, 6000);

  // 2. Tab switching logic
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      const parentCard = btn.closest('.card') || document;
      
      parentCard.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      parentCard.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // 3. Client-side Table Filter Search
  const filterInputs = document.querySelectorAll('[data-table-filter]');
  filterInputs.forEach(input => {
    const tableId = input.getAttribute('data-table-filter');
    const table = document.getElementById(tableId);
    if (!table) return;

    input.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase().trim();
      const rows = table.querySelectorAll('tbody tr');
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
      });
    });
  });

  // 4. Copy to clipboard
  document.querySelectorAll('[data-copy]').forEach(el => {
    el.addEventListener('click', () => {
      const text = el.getAttribute('data-copy');
      navigator.clipboard.writeText(text).then(() => {
        const orig = el.textContent;
        el.textContent = 'Copied!';
        setTimeout(() => el.textContent = orig, 1500);
      });
    });
  });
});

// Render Vis Network Graph with styled nodes & edges
function renderEvidenceGraph(containerId, apiUrl) {
  const container = document.getElementById(containerId);
  if (!container) return;

  fetch(apiUrl)
    .then(r => r.json())
    .then(data => {
      const nodes = data.graph.nodes.map(x => {
        const isDoc = x.type === 'document';
        return {
          id: x.id,
          label: x.label,
          title: x.title || x.label,
          shape: isDoc ? 'box' : 'ellipse',
          color: isDoc ? {
            background: '#eef2ff',
            border: '#6366f1',
            highlight: { background: '#6366f1', border: '#4338ca' }
          } : {
            background: '#fef3c7',
            border: '#f59e0b',
            highlight: { background: '#f59e0b', border: '#d97706' }
          },
          font: { color: '#0f172a', face: 'Inter, sans-serif', size: 13, bold: true },
          margin: 10,
          borderWidth: 2,
          shadow: true
        };
      });

      const edges = data.graph.edges.map(x => {
        const isConflict = x.label === 'contradicts';
        const isMatch = x.label === 'matches';
        return {
          from: x.from,
          to: x.to,
          label: x.label,
          arrows: 'to',
          color: isConflict ? { color: '#ef4444', highlight: '#b91c1c' } :
                 isMatch ? { color: '#f59e0b', highlight: '#d97706' } :
                 { color: '#94a3b8', highlight: '#64748b' },
          font: { color: isConflict ? '#b91c1c' : '#475569', size: 11, background: '#ffffff', strokeWidth: 0 },
          width: isConflict ? 2.5 : 1.5,
          smooth: { type: 'cubicBezier', roundness: 0.2 }
        };
      });

      const options = {
        physics: {
          stabilization: true,
          barnesHut: { gravitationalConstant: -3000, springLength: 120 }
        },
        interaction: { hover: true, tooltipDelay: 100 }
      };

      const network = new vis.Network(container, { nodes, edges }, options);
      network.on('click', (params) => {
        if (params.nodes.length > 0) {
          const clickedNodeId = params.nodes[0];
          const rawNode = data.graph.nodes.find(n => n.id === clickedNodeId);
          if (rawNode && rawNode.doc_id) {
            window.location.href = `/documents/${rawNode.doc_id}`;
          }
        }
      });
    })
    .catch(err => {
      container.innerHTML = `<div style="padding:20px;color:#ef4444">Error loading relationship graph: ${err}</div>`;
    });
}

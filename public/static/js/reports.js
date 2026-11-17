(() => {
  if (typeof Chart === 'undefined') return;
  const make = (canvasId, dataId, xKey, series, chartType = 'line') => {
    const canvas = document.getElementById(canvasId);
    const source = document.getElementById(dataId);
    if (!canvas || !source) return;
    let points;
    try { points = JSON.parse(source.textContent); } catch { return; }
    new Chart(canvas, {
      type: chartType,
      data: {labels: points.map(p => p[xKey]), datasets: series.map(s => ({
        label:s.label, data:points.map(p => Number(p[s.key])), borderColor:s.color,
        backgroundColor:s.color + '28', borderWidth:2, tension:.25, fill:false
      }))},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom'}},
        scales:{y:{beginAtZero:true,ticks:{callback:v=>'$'+v.toLocaleString()}}}}
    });
  };
  make('overviewChart','overviewData','month',[
    {key:'sales',label:'Sales excluding tax',color:'#2563EB'},
    {key:'purchases',label:'Purchases',color:'#7C3AED'}],'bar');
  make('reportChart','reportData','label',[
    {key:'sales',label:'Sales excluding tax',color:'#2563EB'},
    {key:'purchases',label:'Purchases',color:'#7C3AED'},
    {key:'profit',label:'Gross profit',color:'#16A34A'}]);
})();

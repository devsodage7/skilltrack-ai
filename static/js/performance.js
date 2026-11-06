/* Performance charts - plain Chart.js, no build step. */
(function () {
  "use strict";

  const source = document.getElementById("performance-data");
  if (!source || typeof Chart === "undefined") {
    return;
  }

  let data;
  try {
    data = JSON.parse(source.textContent || "{}");
  } catch (error) {
    return;
  }

  const brand = "#4f46e5";
  const brandSoft = "rgba(79, 70, 229, 0.14)";
  const green = "#10b981";
  const amber = "#f59e0b";
  const slate = "#94a3b8";

  const grid = {
    color: "rgba(148, 163, 184, 0.18)",
    drawTicks: false,
  };

  function baseOptions(extra) {
    return Object.assign(
      {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0f172a",
            padding: 10,
            cornerRadius: 8,
            displayColors: false,
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: "#64748b", maxRotation: 0 } },
          y: {
            beginAtZero: true,
            max: 100,
            grid: grid,
            ticks: { color: "#64748b", callback: (value) => value + "%" },
          },
        },
      },
      extra || {}
    );
  }

  function lineChart(id, series, color, fill) {
    const canvas = document.getElementById(id);
    if (!canvas || !series || !series.labels || !series.labels.length) {
      return;
    }
    new Chart(canvas, {
      type: "line",
      data: {
        labels: series.labels,
        datasets: [
          {
            data: series.values,
            borderColor: color,
            backgroundColor: fill,
            fill: true,
            tension: 0.32,
            borderWidth: 2.5,
            pointRadius: 3,
            pointHoverRadius: 5,
            pointBackgroundColor: color,
          },
        ],
      },
      options: baseOptions({
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0f172a",
            padding: 10,
            cornerRadius: 8,
            displayColors: false,
            callbacks: {
              label: function (context) {
                const skill = series.skills ? series.skills[context.dataIndex] : "";
                return (skill ? skill + ": " : "") + context.parsed.y + "%";
              },
            },
          },
        },
      }),
    });
  }

  function barChart(id, series, horizontal, colors) {
    const canvas = document.getElementById(id);
    if (!canvas || !series || !series.labels || !series.labels.length) {
      return;
    }
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: series.labels,
        datasets: [
          {
            data: series.values,
            backgroundColor: colors || brandSoft,
            borderColor: colors ? colors : brand,
            borderWidth: colors ? 0 : 1.5,
            borderRadius: 6,
            maxBarThickness: 26,
          },
        ],
      },
      options: baseOptions({
        indexAxis: horizontal ? "y" : "x",
        scales: horizontal
          ? {
              x: {
                beginAtZero: true,
                max: 100,
                grid: grid,
                ticks: { color: "#64748b", callback: (value) => value + "%" },
              },
              y: { grid: { display: false }, ticks: { color: "#334155" } },
            }
          : {
              x: { grid: { display: false }, ticks: { color: "#64748b", maxRotation: 30 } },
              y: {
                beginAtZero: true,
                max: 100,
                grid: grid,
                ticks: { color: "#64748b", callback: (value) => value + "%" },
              },
            },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0f172a",
            padding: 10,
            cornerRadius: 8,
            displayColors: false,
            callbacks: { label: (context) => context.parsed[horizontal ? "x" : "y"] + "%" },
          },
        },
      }),
    });
  }

  lineChart("scoreTrendChart", data.score_trend, brand, brandSoft);

  barChart(
    "skillAccuracyChart",
    data.skill_accuracy,
    true,
    data.skill_accuracy && data.skill_accuracy.values
      ? data.skill_accuracy.values.map((value) =>
          value >= 75 ? "rgba(16, 185, 129, .75)" : value >= 50 ? "rgba(245, 158, 11, .75)" : "rgba(239, 68, 68, .7)"
        )
      : null
  );

  barChart("careerReadinessChart", data.career_readiness, false, brandSoft);
  lineChart("readinessTrendChart", data.readiness_trend, green, "rgba(16, 185, 129, 0.14)");
})();

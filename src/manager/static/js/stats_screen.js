let processChart, inactivityChart, cpuUsageChart, ipsChart;
const coreColors = {};

function getRandomColor() {
    const r = Math.floor(Math.random() * 256);
    const g = Math.floor(Math.random() * 256);
    const b = Math.floor(Math.random() * 256);
    return `rgba(${r}, ${g}, ${b}, 0.8)`;
}

function refreshData() {
    const button = document.querySelector('.refresh-btn');
    button.disabled = true;
    button.textContent = 'Refreshing...';
    
    const clientName = document.getElementById('clientName').textContent;
    window.location.href = `/stats_screen?client_name=${encodeURIComponent(clientName)}`;
}

// Helper function to create Process Chart
function createProcessChart(canvasElement) {
    return new Chart(canvasElement, {
        type: 'bar',
        data: {
            labels: stats.processes.labels,
            datasets: [{
                data: stats.processes.data,
                backgroundColor: '#00d1b2',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        callback: function(value) {
                            if (value % 1 === 0) return value;
                        }
                    },
                    suggestedMax: Math.max(...stats.processes.data) > 0 ? 
                        Math.max(...stats.processes.data) * 1.2 : 10
                }
            }
        }
    });
}

// Helper function to create Inactivity Chart
function createInactivityChart(canvasElement) {
    const parsedDates = stats.inactivity.labels.map(dateStr => {
        const dateTime = luxon.DateTime.fromFormat(dateStr, 'yyyy-MM-dd HH:mm:ss');
        return dateTime.isValid ? dateTime.toJSDate() : null;
    }).filter(date => date !== null);

    const PADDING_MINUTES = 5;
    let minDate = parsedDates.length ? new Date(Math.min(...parsedDates)) : new Date();
    let maxDate = parsedDates.length ? new Date(Math.max(...parsedDates)) : new Date();

    minDate = new Date(minDate.getTime() - PADDING_MINUTES * 60000);
    maxDate = new Date(maxDate.getTime() + PADDING_MINUTES * 60000);

    return new Chart(canvasElement, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Inactive Time (minutes)',
                data: parsedDates.map((date, index) => ({ 
                    x: date, 
                    y: stats.inactivity.data[index],
                    label: luxon.DateTime.fromJSDate(date).toFormat('yyyy-MM-dd HH:mm:ss')
                })),
                backgroundColor: '#00d1b2',
                pointRadius: 5,
                pointHoverRadius: 7,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        tooltipFormat: 'yyyy-MM-dd HH:mm:ss',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm',
                            day: 'yyyy-MM-dd'
                        }
                    },
                    title: { display: true, text: 'Time' },
                    min: minDate,
                    max: maxDate,
                },
                y: {
                    beginAtZero: true,
                    min: 0,
                    title: { display: true, text: 'Inactive Time (minutes)' },
                    ticks: {
                        precision: 0,
                        callback: function(value) {
                            if (value % 1 === 0) return value;
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const time = context.raw.label || luxon.DateTime.fromJSDate(context.raw.x).toFormat('HH:mm:ss');
                            return [
                                `Time: ${time}`,
                                `Inactive: ${context.raw.y} minutes`
                            ];
                        }
                    }
                }
            }
        }
    });
}

// Helper function to create CPU Usage Chart
function createCpuUsageChart(canvasElement) {
    const cpuDataWithTimestamps = stats.cpu_usage.labels.map((label, i) => ({
        time: luxon.DateTime.fromFormat(label, 'yyyy-MM-dd HH:mm:ss').toJSDate(),
        usage: stats.cpu_usage.data.usage.map(core => core[i]),
    }));
    
    cpuDataWithTimestamps.sort((a, b) => a.time - b.time);
    
    const sortedLabels = cpuDataWithTimestamps.map(d => d.time);
    const sortedUsage = stats.cpu_usage.data.cores.map((_, coreIndex) => 
        cpuDataWithTimestamps.map(d => d.usage[coreIndex]));
    
    return new Chart(canvasElement, {
        type: 'line',
        data: {
            labels: sortedLabels,
            datasets: stats.cpu_usage.data.cores.map((core, index) => {
                const color = coreColors[core] || getRandomColor();
                coreColors[core] = color;
    
                return {
                    label: `Core ${core}`,
                    data: sortedUsage[index],
                    borderColor: color,
                    backgroundColor: 'rgba(0, 209, 178, 0.1)',
                    borderWidth: 2,
                    pointRadius: 5,
                    pointBackgroundColor: color,
                    pointBorderColor: color,
                    fill: true,
                    tension: 0.4,
                };
            })
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        tooltipFormat: 'yyyy-MM-dd HH:mm:ss',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm',
                            day: 'yyyy-MM-dd'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Time'
                    },
                    grid: {
                        display: true,
                        color: 'rgba(255, 255, 255, 0.1)',
                    },
                    ticks: {
                        autoSkip: false,
                        maxRotation: 45,
                        minRotation: 45,
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'CPU Usage (%)'
                    },
                    suggestedMin: 0,
                    suggestedMax: 100,
                    grid: {
                        display: true,
                        color: 'rgba(255, 255, 255, 0.1)',
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const label = context.dataset.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${value}%`;
                        }
                    }
                }
            }
        }
    });
}

// Helper function to create IPs Chart
function createIpsChart(canvasElement) {
    return new Chart(canvasElement, {
        type: 'pie',
        data: {
            labels: stats.ips.labels,
            datasets: [{
                data: stats.ips.data,
                backgroundColor: stats.ips.labels.map(() => getRandomColor()),
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                }
            }
        }
    });
}

// Initialize all charts
document.addEventListener('DOMContentLoaded', () => {
    console.log('Stats Data:', stats);

    processChart = createProcessChart(document.getElementById('processChart'));
    inactivityChart = createInactivityChart(document.getElementById('inactivityChart'));
    cpuUsageChart = createCpuUsageChart(document.getElementById('cpuUsageChart'));
    ipsChart = createIpsChart(document.getElementById('ipsChart'));
});

function expandCard(card) {
    const expandedCard = document.getElementById('expandedCard');
    const overlay = document.getElementById('overlay');

    const cardContent = card.cloneNode(true);
    expandedCard.innerHTML = cardContent.innerHTML;

    const closeButton = document.createElement('button');
    closeButton.className = 'close-btn';
    closeButton.innerText = 'X';
    closeButton.onclick = closeExpandedCard;
    expandedCard.appendChild(closeButton);

    switch(card.id) {
        case 'processes':
            createProcessChart(expandedCard.querySelector('canvas'));
            break;
        case 'inactivity':
            createInactivityChart(expandedCard.querySelector('canvas'));
            break;
        case 'cpu_usage':
            createCpuUsageChart(expandedCard.querySelector('canvas'));
            break;
        case 'ips':
            createIpsChart(expandedCard.querySelector('canvas'));
            break;
    }

    expandedCard.classList.add('active');
    overlay.classList.add('active');
}

function closeExpandedCard() {
    const expandedCard = document.getElementById('expandedCard');
    const overlay = document.getElementById('overlay');

    expandedCard.classList.remove('active');
    overlay.classList.remove('active');
}

document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', () => {
        expandCard(card);
    });
});

function changeClientName() {
    const button = document.querySelector('.name-change-container button');
    button.disabled = true;

    const newName = document.getElementById('newClientName').value.trim();
    if (!newName) {
        alert("Please enter a valid name.");
        button.disabled = false;
        return;
    }

    const forbiddenPattern = /['";\\/*\-]/;
    if (forbiddenPattern.test(newName)) {
        alert("Name contains invalid characters.");
        button.disabled = false;
        return;
    }

    const currentName = document.getElementById('clientName').textContent;

    fetch('/update_client_name', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            current_name: currentName,
            new_name: newName,
        }),
    })
	.then(response => response.json())
	.then(data => {
		if (data.redirect) {
			window.location.href = data.redirect;
		} else if (data.success) {
			document.getElementById('clientName').textContent = newName;
			document.getElementById('newClientName').value = "";
			alert("Client name updated successfully!");
		} else {
			alert(data.message || "Failed to update client name.");
		}
		button.disabled = false;
	});
}
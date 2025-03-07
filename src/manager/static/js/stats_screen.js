let processChart, inactivityChart, cpuUsageChart, ipsChart;
const coreColors = {};

function getRandomColor() {
    const r = Math.floor(Math.random() * 256);
    const g = Math.floor(Math.random() * 256);
    const b = Math.floor(Math.random() * 256);
    return `rgba(${r}, ${g}, ${b}, 0.8)`;
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('Stats Data:', stats);

    processChart = new Chart(document.getElementById('processChart'), {
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
                legend: {
                    display: false
                }
            }
        }
    });

    const parsedDates = stats.inactivity.labels.map(dateStr => {
        const dateTime = luxon.DateTime.fromFormat(dateStr, 'yyyy-MM-dd HH:mm:ss');
        if (!dateTime.isValid) {
            console.error(`Invalid date: ${dateStr}`);
            return null;
        }
        return dateTime.toJSDate();
    }).filter(date => date !== null);

    const minDate = new Date(Math.min(...parsedDates));
    const maxDate = new Date(Math.max(...parsedDates));

    inactivityChart = new Chart(document.getElementById('inactivityChart'), {
        type: 'line',
        data: {
            labels: parsedDates,
            datasets: [{
                label: 'Inactive Time (minutes)',
                data: stats.inactivity.data,
                borderColor: '#00d1b2',
                backgroundColor: 'rgba(0, 209, 178, 0.1)',
                borderWidth: 2,
                pointRadius: 5,
                pointBackgroundColor: '#00d1b2',
                fill: true,
                tension: 0.4,
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
                    title: {
                        display: true,
                        text: 'Time'
                    },
                    min: minDate,
                    max: maxDate,
                },
                y: {
                    title: {
                        display: true,
                        text: 'Inactive Time (minutes)'
                    },
                    suggestedMin: 0,
                    suggestedMax: Math.max(...stats.inactivity.data.filter(Number.isFinite)) * 1.2
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const label = context.dataset.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${value} minutes`;
                        }
                    }
                }
            }
        }
    });

    const parsedLabels = stats.cpu_usage.labels.map(label => luxon.DateTime.fromFormat(label, 'yyyy-MM-dd HH:mm:ss').toJSDate());

    cpuUsageChart = new Chart(document.getElementById('cpuUsageChart'), {
        type: 'line',
        data: {
            labels: parsedLabels,
            datasets: stats.cpu_usage.data.cores.map((core, index) => {
                const color = getRandomColor();
                coreColors[core] = color;

                return {
                    label: `Core ${core}`,
                    data: stats.cpu_usage.data.usage[index],
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

    // IPs Pie Chart
    ipsChart = new Chart(document.getElementById('ipsChart'), {
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

    if (card.id === 'processes') {
        new Chart(expandedCard.querySelector('canvas'), {
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
                    legend: {
                        display: false
                    }
                }
            }
        });
    } else if (card.id === 'inactivity') {
        const parsedDates = stats.inactivity.labels.map(dateStr => {
            const dateTime = luxon.DateTime.fromFormat(dateStr, 'yyyy-MM-dd HH:mm:ss');
            if (!dateTime.isValid) {
                console.error(`Invalid date: ${dateStr}`);
                return null;
            }
            return dateTime.toJSDate();
        }).filter(date => date !== null);

        const minDate = new Date(Math.min(...parsedDates));
        const maxDate = new Date(Math.max(...parsedDates));

        new Chart(expandedCard.querySelector('canvas'), {
            type: 'line',
            data: {
                labels: parsedDates,
                datasets: [{
                    label: 'Inactive Time (minutes)',
                    data: stats.inactivity.data,
                    borderColor: '#00d1b2',
                    backgroundColor: 'rgba(0, 209, 178, 0.1)',
                    borderWidth: 2,
                    pointRadius: 5,
                    pointBackgroundColor: '#00d1b2',
                    fill: true,
                    tension: 0.4,
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
                        title: {
                            display: true,
                            text: 'Time'
                        },
                        min: minDate,
                        max: maxDate,
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Inactive Time (minutes)'
                        },
                        suggestedMin: 0,
                        suggestedMax: Math.max(...stats.inactivity.data.filter(Number.isFinite)) * 1.2
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = context.raw || 0;
                                return `${label}: ${value} minutes`;
                            }
                        }
                    }
                }
            }
        });
    } else if (card.id === 'cpu_usage') {
        const parsedLabels = stats.cpu_usage.labels.map(label => luxon.DateTime.fromFormat(label, 'yyyy-MM-dd HH:mm:ss').toJSDate());

        new Chart(expandedCard.querySelector('canvas'), {
            type: 'line',
            data: {
                labels: parsedLabels,
                datasets: stats.cpu_usage.data.cores.map((core, index) => {
                    const color = coreColors[core];

                    return {
                        label: `Core ${core}`,
                        data: stats.cpu_usage.data.usage[index],
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
    } else if (card.id === 'ips') {
        new Chart(expandedCard.querySelector('canvas'), {
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
        if (data.success) {
            document.getElementById('clientName').textContent = newName;
            document.getElementById('newClientName').value = "";
            alert("Client name updated successfully!");
        } else {
            alert(data.message || "Failed to update client name.");
        }
        button.disabled = false;
    });
}
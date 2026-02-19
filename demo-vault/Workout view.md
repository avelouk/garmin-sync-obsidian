### Workout Calendar

```dataviewjs
const calendarData = {
    colors: {
        orange: ["#ff8c00"],  // Strength: weights, gym, HIIT, yoga
        red:    ["#e73400"],  // Cardio: running, walking
        yellow: ["#f5c400"],  // Cycling: all cycling variants
        green:  ["#49af5d"],  // Team Sports: football, volleyball, basketball...
        blue:   ["#2288ff"],  // Water Sports: surfing, swimming, diving, kayaking...
        brown:  ["#c8813a"],  // Hiking: hiking, trekking, mountaineering
        pink:   ["#ff3a9d"],  // Climbing: bouldering, rock climbing
        white:  ["#d0d0d0"],  // Winter Sports: skiing, snowboarding
    },
    showCurrentDayBorder: true,
    entries: [],
}

for (let page of dv.pages('#workouts')) {
    let metadata = app.metadataCache.getFileCache(page.file);
    if (metadata.frontmatter == null) continue;

    let fm = metadata.frontmatter;
    let type = fm['type'];
    let color = null;

    switch(type) {
        case "Strength":
        case "Strength Training":  // legacy
        case "Calisthenics":       // legacy
        case "Gym":                // legacy
            color = "orange"; break;
        case "Cardio":
        case "Running":            // legacy
        case "Walking":            // legacy
            color = "red"; break;
        case "Cycling":
            color = "yellow"; break;
        case "Team Sports":
        case "Soccer":             // legacy
        case "Volleyball":         // legacy
        case "Sport":              // legacy
            color = "green"; break;
        case "Water Sports":
        case "Surfing":            // legacy
        case "Swimming":           // legacy
            color = "blue"; break;
        case "Hiking":
            color = "brown"; break;
        case "Climbing":
        case "Bouldering":         // legacy
            color = "pink"; break;
        case "Winter Sports":
        case "Skiing":             // legacy
        case "Backcountry Skiing": // legacy
            color = "white"; break;
    }

    calendarData.entries.push({
        date: fm['date_of_workout'],
        color: color
    })
}

// Render one calendar per year, newest first
const currentYear = new Date().getFullYear();
const years = calendarData.entries
    .map(e => parseInt(String(e.date).substring(0, 4)))
    .filter(y => !isNaN(y));
const startYear = years.length > 0 ? Math.min(...years) : currentYear;

for (let year = currentYear; year >= startYear; year--) {
    renderHeatmapCalendar(this.container, { ...calendarData, year })
}
```

### Last month's log

```dataviewjs
let pages = dv.pages("#workouts")
    .where(p => p.date_of_workout >= DateTime.now().minus({months: 1}))
    .sort(p => p.date_of_workout, "desc")

dv.table(
    ["Date", "Exercise", "Type", "Time", "Distance", "Volume", "Pace / Speed", "Avg HR"],
    pages.map(p => [
        p.date_of_workout,
        p.file.link,
        p.type,
        p.time,
        p.distance   ? p.distance + " km"   : "",
        p.volume     ? p.volume + " kg"      : "",
        p.pace       ? p.pace                :
        p.avg_speed  ? p.avg_speed + " km/h" :
        p.max_speed  ? "↑ " + p.max_speed + " km/h" : "",
        p.avg_hr     ? p.avg_hr + " bpm"     : "",
    ])
)
```

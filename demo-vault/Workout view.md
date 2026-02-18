### Workout Calendar

```dataviewjs
const calendarData = {
    colors: {
        orange: ["#ff8c00"],
        green:  ["#49af5d"],
        blue:   ["#2288ff"],
        white:  ["#d0d0d0"],
        pink:   ["#ff3a9d"],
        red:    ["#e73400"],
    },
    showCurrentDayBorder: true,
    entries: [],
}

// Color scheme:
// orange → Strength Training, Gym, Calisthenics
// green  → Soccer, Volleyball (team sports)
// blue   → Surfing, Swimming (water sports)
// white  → Skiing, Backcountry Skiing (snow)
// pink   → Bouldering
// red    → Running, Walking, Hiking, Cycling (distance/cardio)

for (let page of dv.pages('#workouts')) {
    let metadata = app.metadataCache.getFileCache(page.file);
    if (metadata.frontmatter == null) continue;

    let fm = metadata.frontmatter;
    let type = fm['type'];
    let color = null;

    switch(type) {
        case "Strength Training":
        case "Calisthenics":
        case "Gym":
            color = "orange"; break;
        case "Running":
        case "Walking":
        case "Hiking":
        case "Cycling":
            color = "red"; break;
        case "Soccer":
        case "Volleyball":
        case "Sport":
            color = "green"; break;
        case "Surfing":
        case "Swimming":
            color = "blue"; break;
        case "Bouldering":
            color = "pink"; break;
        case "Skiing":
        case "Backcountry Skiing":
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
let pages = dv.pages("#workouts").where(b => b.date_of_workout >= DateTime.now().minus({months:1})).groupBy(b => b.date_of_workout)

for (let group of pages.sort(d => d.key, 'desc')) {
	dv.header(6, group.key);
	dv.table(["File", "Exercise", "Set", "Reps", "Time", "Weight"],
		group.rows
			.sort(k => k.type, 'asc')
			.map(k => [k.file.link, k["exercise"], k["sets"], k["reps"], k["time"], k["weight"]]))
}
```

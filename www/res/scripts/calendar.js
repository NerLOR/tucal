
class Calendar {
    constructor(element) {
        const cal = document.createElement("div");
        cal.classList.add("calendar");

        const table = document.createElement("table");
        const thead = table.createTHead();

        const theadTr1 = document.createElement("tr");
        for (let j = 0; j <= 7; j++) {
            const th = document.createElement("th");
            if (j === 0) {
                th.rowSpan = 2;
                th.innerHTML = `<div class="panel"><span></span><button>HEUTE</button><button>🡄</button><button>🡆</button></div>`;
            }
            theadTr1.appendChild(th);
        }
        thead.appendChild(theadTr1);

        const theadTr2 = document.createElement("tr");
        for (let j = 1; j <= 7; j++) {theadTr2.appendChild(document.createElement("th"));}
        thead.appendChild(theadTr2);

        const tbody = table.createTBody();
        for (let i = 7.0; i <= 21.5; i += 0.5) {
            const tr = document.createElement("tr");
            const th = document.createElement("th");
            if (i >= 8 && i % 1 === 0) {
                th.innerText = `${i < 10 ? "0" + i : i}:00`;
            }
            tr.appendChild(th);
            for (let j = 0; j < 7; j++) {tr.appendChild(document.createElement("td"));}
            tbody.appendChild(tr);
        }

        const buttons = table.getElementsByTagName("button");
        buttons[0].addEventListener("click", (evt) => {});
        buttons[1].addEventListener("click", (evt) => {});
        buttons[2].addEventListener("click", (evt) => {});

        cal.appendChild(table);

        element.appendChild(cal);
    }
}

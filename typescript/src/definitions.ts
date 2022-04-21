"use strict";

interface BuildingJSON {
    id: string,
    name: string | null,
    suffix: string | null,
    area_name: string,
    area_suffix: string | null,
    address: string | null,
}

interface RoomJSON {
    nr: number,
    room_codes: string[],
    tiss_code: string | null,
    name: string | null,
    suffix: string | null,
    name_short: string | null,
    alt_name: string | null,
    name_normalized: string | null,
    lt_room_code: string | null,
    lt_name: string | null,
}

interface CourseJSON {
    nr: string,
    semester: string,
    ects: number,
    type: string,
    name_de: string,
    name_en: string,
    acronym_1: string | null,
    acronym_2: string | null,
    short: string | null,
    program: string | null,
}

interface TucalEventJSON {
    id: string,
    deleted: boolean | null,
    start: string,
    end: string,
    planned_start: string | null,
    planned_end: string | null,
    real_start: string | null,
    real_end: string | null,
    course: {
        nr: string,
        group: string,
        semester: string,
    } | null,
    group: {
        id: string,
        name: string,
    }
    room_nr: number | null,
    data: {
        summary: string | null | undefined,
        desc: string | null | undefined,
        status: string | null | undefined,
        day_event: boolean | null | undefined,
        zoom: string | null | undefined,
        lt: boolean | null | undefined,
        url: string | null | undefined,
        type: string | null | undefined,
        mode: string | null | undefined,
        tiss_url: string | null | undefined,
        tuwel_url: string | null | undefined,
        source_url: string | null | undefined,
        source_name: string | null | undefined,
        organizer: string | null | undefined,
    },
    user: null | {
        hidden: boolean | null | undefined,
    },
}

interface JobStepJSON {
    name: string | null | undefined,
    is_running: boolean | null | undefined,
    time: number | null | undefined,
    steps: JobStepJSON[] | null | undefined,
    comments: string[] | undefined,
}

interface BaseJobStepJSON extends JobStepJSON {
    remaining: number | null | undefined,
    start_ts: string | null | undefined,
    eta_ts: string | null | undefined,
    progress: number | null | undefined,
    error: string | null | undefined,
}

interface JobJSON {
    id: string,
    status: string,
    error_msg: string | null,
    data: BaseJobStepJSON | null,
}

class Building {
    id: string;
    name: string | null;
    suffix: string | null;
    areaName: string;
    areaSuffix: string | null;
    address: string | null;

    constructor(building: BuildingJSON) {
        this.id = building.id;
        this.name = building.name;
        this.suffix = building.suffix;
        this.areaName = building.area_name;
        this.areaSuffix = building.area_suffix;
        this.address = building.address;
    }
}

class Room {
    nr: number;
    roomCodes: string[];
    tissCode: string | null;
    name: string | null;
    suffix: string | null;
    nameShort: string | null;
    altName: string | null;
    nameNormalized: string | null;
    ltRoomCode: string | null;
    ltName: string | null;
    buildingId: string | null;

    constructor(room: RoomJSON) {
        this.nr = room.nr;
        this.roomCodes = room.room_codes || [];
        this.tissCode = room.tiss_code;
        this.name = room.name;
        this.suffix = room.suffix;
        this.nameShort = room.name_short;
        this.altName = room.alt_name;
        this.nameNormalized = room.name_normalized;
        this.ltRoomCode = room.lt_room_code;
        this.ltName = room.lt_name;
        this.buildingId = (this.roomCodes[0] || '').substring(0, 2);
    }

    getName(): string {
        return this.nameShort || this.name || `#${this.nr}`;
    }

    getBuilding(): Building | null {
        if (this.buildingId === null) return null;
        if (!BUILDINGS) throw new Error();
        return BUILDINGS[this.buildingId] || null;
    }

    getNameLong(): string {
        let str = this.name || `#${this.nr}`;
        if (this.suffix) str += ' – ' + this.suffix;
        if (this.altName) str += ' (' + this.altName + ')';
        return str;
    }

    getLectureTubeLink(): string | null {
        if (!this.ltRoomCode || !this.ltName) return null;

        switch (LT_PROVIDER) {
            case 'hs-streamer': return `https://hs-streamer.fsbu.at/?hs=${this.ltRoomCode}`;
            case 'live-video-tuwien': return `https://live.video.tuwien.ac.at/room/${this.ltRoomCode.toLowerCase()}/player.html`;
            default: throw new Error(`Unknown LectureTube provider '${LT_PROVIDER}'`);
        }
    }

    getCodeFormat(): string {
        return this.roomCodes.map(
            (c) => `${c.substring(0, 2)} ${c.substring(2, 4)} ${c.substring(4)}`
        ).join(', ');
    }

    getAddress(): string {
        const roomCode = this.roomCodes[0];
        if (!roomCode) return '';

        const floorStr = formatFloor(roomCode.substring(2, 4));
        const building = this.getBuilding();

        let address = floorStr;
        if (building) {
            if (building.name || building.address) address += '\n';
            if (building.name) {
                address += building.name;
                if (building.suffix) address += ' – ' + building.suffix;
                address += ' (';
            }
            if (building.address) address += building.address;
            if (building.name) address += ')';

            if (building.areaName) address += '\n' + building.areaName;
            if (building.areaSuffix) address += ' – ' + building.areaSuffix;
        }

        return address;
    }

    static pseudo(nr: number): Room {
        return new Room(<RoomJSON>{
            nr: nr
        });
    }
}

class CourseDef {
    nr: string;
    ects: number;
    type: string;
    name_de: string;
    name_en: string;
    acronym1: string | null;
    acronym2: string | null;
    short: string | null;
    program: string | null;

    constructor(course: CourseJSON) {
        this.nr = course.nr;
        this.ects = course.ects;
        this.type = course.type;
        this.name_de = course.name_de;
        this.name_en = course.name_en;
        this.acronym1 = course.acronym_1;
        this.acronym2 = course.acronym_2;
        this.short = course.short;
        this.program = course.program;
    }

    getCourseNr() {
        return this.nr.slice(0, 3) + '.' + this.nr.slice(3);
    }

    getName(): string {
        return this.acronym1 || this.acronym2 || this.short || this.name_de;
    }
}

class Week {
    year: number;
    week: number;

    constructor(year: number, week: number) {
        this.year = year;
        this.week = week;
    }

    static fromDate(date: Date): Week {
        return isoWeekFromDate(date);
    }

    toString(): string {
        return `${this.year}/W${this.week}`;
    }

    valueOf(): number {
        return this.year * 100 + this.week;
    }

    startDate(): Date {
        return asTimezone(isoWeekToDate(this.year, this.week), TIMEZONE);
    }

    endDate(): Date {
        const ref = this.startDate();
        ref.setDate(ref.getDate() + 7);
        return ref;
    }

    add(n: number): Week {
        const ref = this.startDate();
        ref.setDate(ref.getDate() + 7 * n);
        return isoWeekFromDate(ref);
    }

    next(): Week {
        return this.add(1);
    }

    last(): Week {
        return this.add(-1);
    }

    iterate(n: number | Week, step: number = 1) {
        let i: Week;
        let end: Week;
        if (n instanceof Week) {
            i = this.add(0);
            end = n.add(0);
        } else if (n < 0 && step > 0) {
            i = this.add(n);
            end = this.add(0);
        } else {
            i = this.add(0);
            end = this.add(n)
        }
        return {
            *[Symbol.iterator]() {
                while (true) {
                    yield i;
                    if (i.year === end.year && i.week === end.week) {
                        return;
                    }
                    i = i.add(step);
                }
            }
        }
    }
}

class TucalEvent {
    id: string;
    deleted: boolean | null;
    status: string | null;
    dayEvent: boolean;
    start: Date;
    end: Date;
    plannedStart: Date | null;
    plannedEnd: Date | null;
    realStart: Date | null;
    realEnd: Date | null;
    courseNr: string | null;
    semester: string | null;
    courseGroup: string | null;
    groupId: string;
    groupName: string;
    summary: string | null;
    desc: string | null;
    roomNr: number | null;
    zoom: string | null;
    lectureTube: boolean | null;
    url: string | null;
    tissUrl: string | null;
    tuwelUrl: string | null;
    sourceUrl: string | null;
    sourceName: string | null;
    organizer: string | null;
    type: string | null;
    mode: string | null;
    userHidden: boolean = false;

    constructor(event: TucalEventJSON) {
        this.id = event.id;
        this.roomNr = event.room_nr;
        this.deleted = event.deleted;
        this.status = event.data.status || null;
        this.dayEvent = event.data.day_event || false;
        this.start = asTimezone(new Date(Date.parse(event.start)), TIMEZONE);
        this.end = asTimezone(new Date(Date.parse(event.end)), TIMEZONE);

        this.plannedStart = (event.planned_start) ? asTimezone(new Date(Date.parse(event.planned_start)), TIMEZONE) : null;
        this.plannedEnd = (event.planned_end) ? asTimezone(new Date(Date.parse(event.planned_end)), TIMEZONE) : null;
        this.realStart = (event.real_start) ? asTimezone(new Date(Date.parse(event.real_start)), TIMEZONE) : null;
        this.realEnd = (event.real_end) ? asTimezone(new Date(Date.parse(event.real_end)), TIMEZONE) : null;

        if (event.course) {
            this.courseNr = event.course.nr;
            this.courseGroup = event.course.group;
            this.semester = event.course.semester;
        } else {
            this.courseNr = null;
            this.courseGroup = null;
            this.semester = null;
        }

        this.groupId = event.group.id;
        this.groupName = event.group.name;
        this.summary = event.data.summary || null;
        this.desc = event.data.desc || null;
        this.zoom = event.data.zoom || null;
        this.lectureTube = event.data.lt || null;
        this.url = event.data.url || null;
        this.tissUrl = event.data.tiss_url || null;
        this.tuwelUrl = event.data.tuwel_url || null;
        this.sourceUrl = event.data.source_url || null;
        this.sourceName = event.data.source_name || null;
        this.organizer = event.data.organizer || null;
        this.type = event.data.type || null;
        this.mode = event.data.mode || null;

        if (event.user) {
            this.userHidden = event.user.hidden || false;
        }
    }

    getRoom(): Room | null {
        if (this.roomNr === null) return null;
        if (!ROOMS) return Room.pseudo(this.roomNr);
        return ROOMS[this.roomNr] || null;
    }

    getCourse(): CourseDef | null {
        if (!COURSE_DEF) throw new Error();
        return this.courseNr && COURSE_DEF[this.courseNr] || null;
    }

    getWeek(): Week {
        return Week.fromDate(this.start);
    }

    getStartMinutes(): number {
        return this.start.getHours() * 60 + this.start.getMinutes();
    }

    getEndMinutes(): number {
        return this.end.getHours() * 60 + this.end.getMinutes();
    }

    isNow(): boolean {
        const dt = asTimezone(new Date(), TIMEZONE);
        return dt >= this.start && dt < this.end;
    }
}

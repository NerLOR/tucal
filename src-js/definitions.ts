"use strict";

interface ApiJSON {

}

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

interface CourseDefJSON {
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

interface CourseJSON {

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
        this.roomCodes = room.room_codes;
        this.tissCode = room.tiss_code;
        this.name = room.name;
        this.suffix = room.suffix;
        this.nameShort = room.name_short;
        this.altName = room.alt_name;
        this.nameNormalized = room.name_normalized;
        this.ltRoomCode = room.lt_room_code;
        this.ltName = room.lt_name;
        this.buildingId = (this.roomCodes[0] || '').substr(0, 2);
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
        if (this.suffix) str += ' ' + this.suffix;
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

    static pseudo(nr: number): Room {
        return new Room(<RoomJSON>{
            nr: nr
        });
    }
}

class CourseDef {
    nr: string;
    semester: string;
    ects: number;
    type: string;
    name_de: string;
    name_en: string;
    acronym1: string | null;
    acronym2: string | null;
    short: string | null;
    program: string | null;

    constructor(course: CourseDefJSON) {
        this.nr = course.nr;
        this.semester = course.semester;
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

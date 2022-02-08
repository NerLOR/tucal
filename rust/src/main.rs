
#[macro_use] extern crate rocket;

use std::path::PathBuf;
use rocket::fs::FileServer;
use rocket_dyn_templates::Template;
use rocket_async_compression::Compression;
use rocket::Request;
use rocket::http::Status;
use rocket::serde::json::{Json, Value};
use rocket::serde::json::serde_json::json;


#[get("/")]
fn index() -> Template {
    let ctx: Value = json!({
        "locale_msg": {
            "Imprint": "Impressum",
            "Contact": "Kontakt",
            "Home": "Startseite",
        },
        "icon": "tucal",
        "tucal": {
            "hostname": "tucal.local",
        },
        "lang": "de-AT",
        "date": {
            "y": 2022i64,
            "m": 2i64,
            "d": 7i64,
        },
        "http_messages": {
            "400": "Bad Request",
            "401": "Unauthorized",
            "403": "Forbidden",
            "404": "Not Found",
            "409": "Conflict",
            "410": "Gone",
            "500": "Internal Server Error",
            "501": "Not Implemented",
        },
        "uri": "/",
        "calendar_uri": "/calendar/12345678/",
    });
    Template::render("index", &ctx)
}

#[catch(default)]
fn default_catcher(status: Status, request: &Request) -> Template {
    let ctx: Value = json!({
        "locale_msg": {
            "Imprint": "Impressum",
            "Contact": "Kontakt",
            "Home": "Startseite",
        },
        "icon": "tucal",
        "tucal": {
            "hostname": "tucal.local",
        },
        "lang": "de-AT",
        "date": {
            "y": 2022i64,
            "m": 2i64,
            "d": 7i64,
        },
        "http_messages": {
            "400": "Bad Request",
            "401": "Unauthorized",
            "403": "Forbidden",
            "404": "Not Found",
            "409": "Conflict",
            "410": "Gone",
            "500": "Internal Server Error",
            "501": "Not Implemented",
        },
        "status": status.code,
        "uri": request.uri(),
        "calendar_uri": "/calendar/12345678/",
    });
    Template::render("error", &ctx)
}


#[get("/<path..>")]
fn api(path: PathBuf) -> Value {
    json!({
        "status": "error",
        "reason": "Resource was not found.",
    })
}

#[launch]
fn rocket() -> _ {
    rocket::build()
        .mount("/api", routes![api])
        .mount("/", routes![index])
        .mount("/res", FileServer::from("../dest/www/res"))
        .register("/", catchers![default_catcher])
        .attach(Template::fairing())
        .attach(Compression::fairing())
}

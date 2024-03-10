# schedule_maker_9000
A placeholder repo for an app idea for DjangoCon 2024. I'd like to be able to pick my talks and have the app generate a schedule for me.
Currently using the PyCon schedule to build out a proof of concept.

## Setup

- Create `.env` from example file.
- `docker compose up`
- View at http://localhost:9000/

## Notes
Helper snippet to generate passwords:

`openssl rand -base64 128 | tr -d '/$\n' | head -c 64; echo`

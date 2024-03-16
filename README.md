# schedule_maker_9000

A placeholder repo for an app idea for DjangoCon 2024. I'd like to be able to pick my talks and have the app generate a
schedule for me. Currently using the PyCon schedule to build out a proof of concept.

This is very much a WIP and plenty of things are broken or incomplete. I don't have a fully articulated plan either.
I'm just figuring it out as I go.

## Setup

- Create `.env` from example file.
- `docker compose up`
- View at http://localhost:9000/

## Notes

Helper snippet to generate passwords:

`openssl rand -base64 128 | tr -d '/$\n' | head -c 64; echo`

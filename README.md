# schedule_maker_9000
A placeholder repo for an app idea.

## Setup

- Create `.env` from example file.
- `docker compose up`
- View at http://localhost:9000

## Notes
Helper snipped to generate passwords:

`openssl rand -base64 128 | tr -d '/$\n' | head -c 64; echo`

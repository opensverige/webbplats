# Build for Anthropic's OSS Scanner. The scan itself runs without network, so
# everything the tests need is fetched here: Deno and the jsr: imports for the
# membership function, Python for the site tools, and a local Postgres with
# supabase/schema.sql loaded so the database constraints can be exercised.
FROM denoland/deno:debian-2.1.4

USER root
ENV DEBIAN_FRONTEND=noninteractive \
    DENO_NO_UPDATE_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates git python3 postgresql \
    && rm -rf /var/lib/apt/lists/*

# scanner contract: the checkout lives inside the image, at /src
COPY . /src
WORKDIR /src

# Cache every jsr: import while the network is up, then typecheck. A type error
# fails the build: it is the same check that runs before every deploy.
RUN cd supabase/functions/medlem \
    && deno cache index.ts hjalp_test.ts \
    && deno check index.ts

# Postgres with the real schema in a database called medlem. Start it in the
# scan with: service postgresql start
RUN service postgresql start \
    && su postgres -c "createdb medlem" \
    && su postgres -c "psql -v ON_ERROR_STOP=1 -d medlem -f /src/supabase/schema.sql" \
    && service postgresql stop

# Cheap tests. Failures are logged, not fatal, so the scan still runs.
RUN cd supabase/functions/medlem \
    && (deno test --allow-net=jsr.io hjalp_test.ts || echo "WARNING: deno test failed")
RUN python3 tools/migrera-blogg.py --kontroll || echo "WARNING: blog check failed"
RUN python3 tools/verifiera.py || echo "WARNING: site check failed"

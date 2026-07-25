# Deploying the web generator

## What "owning it" actually means here

The app is stateless. No database, no uploads, no sessions — the zip is built in
memory and handed to the browser as a data URL. The only persistent thing on the
whole box is Caddy's TLS certificate cache.

That's what makes ownership real: the deployable unit is a plain Docker
container plus your domain. Any host that runs a container runs this, and
moving between hosts is a DNS change and a `docker compose up`. You are not
locked into anything, and nothing needs to be exported if you leave.

So the hosting choice is about ergonomics and cost, not lock-in.

## Recommended: a VPS you rent, running Docker + Caddy

**Hetzner** is the price-to-performance pick. Their entry cloud plans run
roughly €4–6/month for 2 vCPU and 4 GB RAM with a very large traffic
allowance, and they have US datacenters in Ashburn, VA and Hillsboro, OR
alongside the European ones. Check current plan names, regional availability,
and pricing when you sign up — Hetzner adjusted prices in June 2026 and the
CX line's region availability has moved around.

DigitalOcean and Vultr cost a bit more and have friendlier dashboards. Any of
the three is fine; the compose file doesn't care.

### First-time setup, start to finish

**1. Point the domain.** Create an `A` record for your domain at the server's
IPv4 address before you start the containers — Caddy needs it resolvable to
issue a certificate.

**2. Create the server.** Ubuntu 24.04, smallest plan. Add your SSH key during
creation so password login is never enabled.

**3. Basic hardening.** As root, once:

```bash
adduser --gecos "" deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy

# Disable root SSH and password auth
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

# Automatic security patches
apt update && apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

**4. Install Docker.** As `deploy`:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# log out and back in for the group to take effect
```

**5. Deploy.**

```bash
git clone <your-repo-url> cff && cd cff
cp .env.example .env
nano .env          # set SITE_DOMAIN, and ESP keys if you have them yet
docker compose up -d --build
```

Caddy will fetch a certificate within a few seconds. Visit your domain.

**6. Updating, from then on:**

```bash
git pull && docker compose up -d --build
```

### Checking on it

```bash
docker compose ps                 # both containers should be healthy
docker compose logs -f app        # application logs
docker compose exec caddy cat /data/access.log | tail   # who's visiting, and via which path
```

The Caddyfile rewrites `/mcp`, `/tool`, `/li`, and `/book` to the same page, so
the access log tells you which surface sent each visitor without any tracking
script.

## If you'll host more than this one thing

You have a book landing page, Horizon South, and VAEL that could all live on
one box. At that point a self-hosted PaaS earns its keep.

**Coolify** is the mature option — Apache-2.0, installs with one command, and
gives you a dashboard with git-push deploys, automatic Let's Encrypt, and
environment-variable management across multiple apps. It wraps Docker and a
reverse proxy, so what it deploys is still a standard container: your code
stays in your git repo and there's no vendor format to escape from later.

Two costs to know going in. It idles at roughly 800 MB of RAM before your apps
run, so size the VPS accordingly. And it manages deployments, not the server —
OS patching, firewall, and disk are still yours.

Dokploy and CapRover are lighter alternatives if the dashboard is all you want.

**My read:** for one app, skip it. The compose file above is fifteen minutes
and less to go wrong. Add Coolify when the second or third site arrives.

## What not to use

- **Replit, Render free tier, and similar** — the free tiers sleep. A tool
  linked from a LinkedIn post that takes 40 seconds to wake is worse than no
  tool. Paid tiers work fine but cost more than the VPS for less control.
- **Anything requiring a proprietary config format.** You'd be trading the
  portability the Dockerfile gives you for a marginally nicer dashboard.

## Backups

There's almost nothing to back up, which is the point. The code is in git; the
certificates regenerate on their own. The one thing worth keeping is the access
log if you care about attribution history — copy it off periodically, or ship
it somewhere if you get serious about measurement.

Once an ESP is wired in, your email list lives with the ESP. That's the only
data of real value in the system, and it's already off the box.

# Security policy

ZenithBoard runs as root on a machine in your home, listens on your network, and installs software written by other people. The full picture — what is exposed, what the code checks, and what is trusted because it cannot be checked — is on the wiki:

**https://github.com/regis57/ZenithBoard/wiki/Security**

## Reporting something

Use GitHub's **private vulnerability reporting** on this repository (*Security → Report a vulnerability*), or open a normal issue if the problem is not sensitive.

Please include what you found, how to reproduce it, and what it would let someone do. A proof of concept helps but is not required, and a careful description of a design weakness is just as welcome as a working exploit.

This is a spare-time project: there is no security team and no response-time promise. What there is: a real report will be read, answered and credited, and a fix will not be quietly slipped in without saying what it was for.

## Supported versions

The newest release only. There are no backports — upgrading is `cd ~/ZenithBoard && sudo zenithboard update`.

## Two things worth knowing before you report

**The wall has no login, by design.** It is meant to be opened by a tablet with no keyboard, on a home network. That is not a vulnerability; forwarding it to the internet is a mistake, and the documentation says so. A way to reach it from *outside* your network without you forwarding it would be a real finding.

**Third-party installers are trusted on purpose.** Installing ZenithBoard runs readsb's, ADSB Exchange's and Flightradar24's own installers as root. That trust is documented rather than hidden. A hole in one of those belongs to that project; a way for ZenithBoard to run something *other* than what those projects published belongs here.

What happens when one of those projects moves a file or changes a key is written down in **[When a provider changes something](https://github.com/regis57/ZenithBoard/wiki/Providers)**.

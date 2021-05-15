# Docker PlayOnLinux App Template

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

docker build -t polapp .

docker network create polapp-net // Check this is needed

docker volume create polapp-volume

docker run --volume=polapp-volume:/data --net=polapp-net --name=playonlinux-app --publish=8080:8080 polapp


*Uses Ubuntu in place of Debian to get playonlinux via apt.

*Switched the version of Go to just numbered (not sure if this makes a difference?)

*Specified the timezone in Dockerfile to avoid a hang on build.

*Specified the app user as an environment variable for PlayOnLinux

*Menu not being found.

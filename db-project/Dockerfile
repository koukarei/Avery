FROM mysql:9

# run command file
CMD [ "mysql", "-u", "root", "-p", "password", "-e", "source /docker-entrypoint-initdb.d/01_init.sql" ]
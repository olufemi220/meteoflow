ARG NIFI_VERSION=2.6.0
FROM apache/nifi:${NIFI_VERSION}
ARG NIFI_VERSION

# Pilote JDBC PostgreSQL, utilisé par le DBCPConnectionPool
ADD --chown=nifi:nifi https://jdbc.postgresql.org/download/postgresql-42.7.4.jar /opt/nifi/nifi-current/drivers/postgresql.jar

# À décommenter SEULEMENT si PutMongoRecord n'apparaît pas dans NiFi (voir Dépannage)
# ADD --chown=nifi:nifi https://repo1.maven.org/maven2/org/apache/nifi/nifi-mongodb-client-service-api-nar/${NIFI_VERSION}/nifi-mongodb-client-service-api-nar-${NIFI_VERSION}.nar /opt/nifi/nifi-current/lib/
# ADD --chown=nifi:nifi https://repo1.maven.org/maven2/org/apache/nifi/nifi-mongodb-services-nar/${NIFI_VERSION}/nifi-mongodb-services-nar-${NIFI_VERSION}.nar /opt/nifi/nifi-current/lib/
# ADD --chown=nifi:nifi https://repo1.maven.org/maven2/org/apache/nifi/nifi-mongodb-nar/${NIFI_VERSION}/nifi-mongodb-nar-${NIFI_VERSION}.nar /opt/nifi/nifi-current/lib/

#
# Build
#
# debian:10 (Buster) is EOL and its apt repos are archived, so installing maven
# via apt no longer works. Use the official Maven image bundling JDK 8 instead.
FROM maven:3.9-eclipse-temurin-8 AS build

WORKDIR /opt/shipping

COPY pom.xml /opt/shipping/
RUN mvn dependency:resolve
COPY src /opt/shipping/src/
RUN mvn package

#
# Run
#
# openjdk:8-jdk was removed from Docker Hub; eclipse-temurin is the official
# OpenJDK 8 replacement image.
FROM eclipse-temurin:8-jdk

EXPOSE 8080

WORKDIR /opt/shipping

ENV CART_ENDPOINT=cart:8080
ENV DB_HOST=mysql

COPY --from=build /opt/shipping/target/shipping-1.0.jar shipping.jar

CMD [ "java", "-Xmn256m", "-Xmx768m", "-jar", "shipping.jar" ]


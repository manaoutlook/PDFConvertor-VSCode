{pkgs}: {
  deps = [
    pkgs.jdk8
    pkgs.jre
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}

FROM nixos/nix
COPY c/shell.nix .
RUN 'nix-shell'
WORKDIR c
RUN make all

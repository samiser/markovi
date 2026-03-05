{
  description = "Markovi - Discord bot using Markov chains";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
    pyproject-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    { nixpkgs, pyproject-nix, ... }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;

      project = pyproject-nix.lib.project.loadPyproject {
        projectRoot = ./.;
      };

      pythonAttr = "python312";
    in
    {
      devShells = forAllSystems (system: {
        default =
          let
            pkgs = nixpkgs.legacyPackages.${system};
            python = pkgs.${pythonAttr};
            pythonEnv = python.withPackages (ps: [
              ps.discordpy
              ps.redis
            ]);
          in
          pkgs.mkShell {
            packages = [
              pythonEnv
              pkgs.redis
            ];
            shellHook = ''
              export PYTHONPATH="${./.}:$PYTHONPATH"
            '';
          };
      });

      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.${pythonAttr};
          markovi = python.pkgs.buildPythonPackage {
            pname = "markovi";
            version = "0.1.0";
            src = ./.;
            format = "pyproject";
            nativeBuildInputs = [ python.pkgs.setuptools ];
            propagatedBuildInputs = [
              python.pkgs.discordpy
              python.pkgs.redis
            ];
          };
        in
        {
          default = markovi;

          docker = pkgs.dockerTools.buildLayeredImage {
            name = "markovi";
            tag = "latest";
            contents = [
              markovi
              pkgs.redis
              pkgs.bash
              pkgs.coreutils
            ];
            config = {
              Cmd = [ "${pkgs.bash}/bin/bash" "-c" ''
                redis-server --daemonize yes && markovi
              '' ];
              Env = [
                "REDIS_URL=redis://localhost:6379/0"
              ];
            };
          };
        }
      );
    };
}

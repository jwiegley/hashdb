{
  description = "hashdb - file checksum database for duplicate detection";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.python3Packages.buildPythonApplication {
            pname = "hashdb";
            version = "0.1.0";
            src = self;
            pyproject = true;
            build-system = [ pkgs.python3Packages.setuptools ];
          };
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = [
              (pkgs.python3.withPackages (ps: [
                ps.pytest
                ps.pytest-cov
                ps.hypothesis
              ]))
              pkgs.ruff
              pkgs.lefthook
            ];
          };
        }
      );

      checks = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonWithDeps = pkgs.python3.withPackages (ps: [
            ps.pytest
            ps.pytest-cov
            ps.hypothesis
          ]);
          mkCheck =
            name: checkScript:
            pkgs.stdenv.mkDerivation {
              name = "hashdb-check-${name}";
              src = self;
              dontBuild = true;
              doCheck = true;
              nativeBuildInputs = [
                pythonWithDeps
                pkgs.ruff
              ];
              checkPhase = checkScript;
              installPhase = "touch $out";
            };
        in
        {
          format = mkCheck "format" ''
            ruff format --check .
          '';

          lint = mkCheck "lint" ''
            ruff check .
          '';

          test = mkCheck "test" ''
            PYTHONPATH=src python -m pytest tests/ -x -q
          '';

          coverage = mkCheck "coverage" ''
            PYTHONPATH=src python -m pytest tests/ \
              --cov=hashdb --cov-report=term-missing --cov-fail-under=70
          '';

          fuzz = mkCheck "fuzz" ''
            PYTHONPATH=src python -m pytest tests/test_fuzz.py -x -q
          '';

          build = self.packages.${system}.default;
        }
      );
    };
}

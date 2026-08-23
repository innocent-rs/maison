{
  description = "Environnement Python pour build123d et ocp_vscode";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python312
              uv
              just
              curl
            ];

            # Bibliothèques chargées dynamiquement par les wheels OCP/OpenGL.
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (with pkgs; [
              stdenv.cc.cc.lib
              zlib
              libGL
              libx11
              libxcb
              libxext
              libxrender
              libxi
              libxkbcommon
              fontconfig
              freetype
              expat
              glib
            ]);

            shellHook = ''
              export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
              # Les wheels manylinux de NumPy/Scipy embarquent OpenBLAS. Sur
              # NixOS, on expose explicitement ces répertoires au chargeur.
              pythonSite="$PWD/.venv/lib/python3.12/site-packages"
              export LD_LIBRARY_PATH="$pythonSite/numpy.libs:$pythonSite/scipy.libs:$LD_LIBRARY_PATH"
              if [[ -f "$PWD/uv.lock" ]]; then
                uv sync --frozen --quiet
                source "$PWD/.venv/bin/activate"
              fi
              echo "Environnement prêt. Lancez : python -m ocp_vscode --tree_width 240"
            '';
          };
        });
    };
}

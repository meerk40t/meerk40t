# Maintainer: MeerK40t Team <maintainer@meerk40t.org>
pkgname=meerk40t
pkgver=0.9.8220
pkgrel=1
pkgdesc="A free, open-source laser engraving software"
arch=('x86_64' 'i686' 'aarch64')
url="https://github.com/meerk40t/meerk40t"
license=('MIT')
depends=('python' 'python-numpy' 'python-pyusb' 'python-pyserial')
makedepends=('python-build' 'python-installer' 'python-wheel')
optdepends=('wxpython: GUI support'
            'python-pillow: Image support'
            'opencv-python-headless: Computer vision support'
            'python-ezdxf: DXF import support')
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/meerk40t/${pkgname}/archive/refs/tags/v${pkgver}.tar.gz")
sha256sums=('SKIP')  # Will be updated by CI/CD workflow

build() {
    cd "${pkgname}-${pkgver}"
    python -m build --wheel --no-isolation
}

package() {
    cd "${pkgname}-${pkgver}"
    python -m installer --destdir="$pkgdir" dist/*.whl
    
    # Install license
    install -Dm 644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    
    # Install documentation
    install -Dm 644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}

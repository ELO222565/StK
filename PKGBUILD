# PKGBUILD

pkgname=StK
pkgver=1.0
pkgrel=1
pkgdesc="StK Terminal Emulator"
arch=('any')
url="https://github.com/ELO222565/StK"
license=('CC BY-NC')
depends=('python')

source=("$pkgname-$pkgver.tar.xz::https://github.com/StK/releases/download/cool/StK-.tar.xz")

build() {
    cd "$pkgname-$pkgver"
    python setup.py build
}

package() {
    cd "$pkgname-$pkgver"
    python setup.py install --root="$pkgdir/" --optimize=1
}

class Scinumtools3 < Formula
  desc "C++ toolkit for unit-aware scientific computation"
  homepage "https://github.com/scinumtools/snt3"
  url "https://github.com/scinumtools/snt3/archive/refs/tags/v0.9.7.tar.gz"
  sha256 "2d854e7f7ee87f6ccf285fb1a4aa70d09691cf5b353ea0618f56c91bd0341668"
  license "MIT"
  head "https://github.com/scinumtools/snt3.git", branch: "main"

  depends_on "cmake" => :build
  depends_on "ninja" => :build
  depends_on "hdf5"

  on_linux do
    depends_on "pkgconf" => :build
    depends_on "freeglut"
    depends_on "libxcursor"
    depends_on "libxext"
    depends_on "libxi"
    depends_on "libxinerama"
    depends_on "libxkbcommon"
    depends_on "mesa"
  end

  resource "briefpp" do
    url "https://github.com/vrtulka23/briefpp/archive/624aa478149a0fa0e7213bb7cfb6d19615d6e771.tar.gz"
    sha256 "aaac2a8a25f8a7bc11546038594eb9fef43bf560c0c0532a886c432d5e14de31"
  end

  resource "cpp-httplib" do
    url "https://github.com/yhirose/cpp-httplib/archive/008e107d0fcddee7cb96dc5ad3c3189fd090e40a.tar.gz"
    sha256 "3966e3b69a3329e238534de3af1d07ee4e88607a60946b3af1af3036f381b63b"
  end

  resource "glfw" do
    url "https://github.com/glfw/glfw/archive/d9d6f0f1f967807ffade6598ea9a631ebaf37a56.tar.gz"
    sha256 "96722514789b1aa1ad9c4debd874450156ea457aea691e546ffaf5b53892d5a3"
  end

  resource "imgui" do
    url "https://github.com/ocornut/imgui/archive/f1cc2ae15e53a861a874c3034aae6798fde194ab.tar.gz"
    sha256 "f30be7f3e2136615b1848a9afb72f6dfd8a60820ddf1c1a85997bf3b722e7cfc"
  end

  def install
    resource("briefpp").stage buildpath/"external/briefpp"
    resource("cpp-httplib").stage buildpath/"external/cpp-httplib"
    resource("glfw").stage buildpath/"external/glfw"
    resource("imgui").stage buildpath/"external/imgui"

    args = std_cmake_args + %w[
      -GNinja
      -DENABLE_UNIT_TESTS=OFF
      -DENABLE_BINDING_PYTHON=OFF

      -DENABLE_CORE=ON
      -DENABLE_EXS=ON
      -DENABLE_VAL=ON
      -DENABLE_PUQ=ON
      -DENABLE_DIP=ON
      -DENABLE_MAT=OFF
      -DENABLE_API=ON

      -DENABLE_SNT_DMAP=OFF
      -DENABLE_SNT_SERVER=ON
      -DENABLE_SNT_VIEW=ON
      -DENABLE_SNT_REPORT=ON
      -DENABLE_EXEC_EXAMPLES=OFF
      -DENABLE_EXEC_BENCHMARKS=OFF
    ]

    system "cmake", "-S", ".", "-B", "build", *args
    system "cmake", "--build", "build"
    system "cmake", "--install", "build"
  end

  test do
    output = shell_output("#{bin}/snt -v")
    assert_match version.to_s, output
    assert_match "snt server [options]", shell_output("#{bin}/snt server --help")
    assert_match "snt view <artifact>", shell_output("#{bin}/snt view --help")
    assert_match "snt report", shell_output("#{bin}/snt report --help")
  end
end

class Typist < Formula
  desc "Voice typing assistant and driver for Ulanzi Vibe Key AU05"
  homepage "https://github.com/kubja/ulanzi-vibekey"
  url "https://github.com/kubja/ulanzi-vibekey/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  service do
    run [opt_bin/"typist"]
    keep_alive true
    log_path var/"log/typist.log"
    error_log_path var/"log/typist.error.log"
  end

  test do
    system "#{bin}/typist", "--help"
  end
end

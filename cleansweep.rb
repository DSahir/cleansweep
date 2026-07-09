class Cleansweep < Formula
  desc "Lightweight system optimizer and developer dashboard"
  homepage "https://github.com/DSahir/cleansweep"
  url "https://github.com/DSahir/cleansweep/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "da39a3ee5e6b4b0d3255bfef95601890afd80709" # Dummy fallback
  license "MIT"

  head "https://github.com/DSahir/cleansweep.git", branch: "main"

  depends_on "python@3.12"

  def install
    # Setup virtualenv inside libexec
    venv_dir = libexec/".venv"
    system "python3.12", "-m", "venv", venv_dir
    
    # Install dependencies inside the virtualenv
    system venv_dir/"bin/pip", "install", "-r", "requirements.txt"
    
    # Copy app structure to libexec
    libexec.install "app.py", "config.py", "cleaner", "scanner", "templates"

    # Create launch wrapper script in bin
    (bin/"cleansweep").write <<~EOS
      #!/bin/bash
      exec "#{venv_dir}/bin/python" "#{libexec}/app.py" "$@"
    EOS
    chmod 0755, bin/"cleansweep"
  end

  def caveats
    <<~EOS
      To start the CleanSweep dashboard:
        cleansweep
      
      This will start the local webserver and launch your default browser automatically.
    EOS
  end
end

# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure("2") do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # This is a box we've prepared for the assignment. It's based on ubuntu/bionic64
  config.vm.box = "brucespang/cs244-2020-pa1"
  config.vm.box_version = "1.0.0"

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine and only allow access
  # via 127.0.0.1 to disable public access
  
  #  Forward port 8888 (Jupyter notebooks) to 127.0.0.1:8888 on the host machine.
  config.vm.network "forwarded_port", guest: 8888, host: 8888, host_ip: "127.0.0.1"

  # Provider-specific configuration so you can fine-tune various
  # backing providers for Vagrant. These expose provider-specific options.
  # Example for VirtualBox:
  config.vm.provider "virtualbox" do |vb|
    # Display the VirtualBox GUI when booting the machine
    # vb.gui = true
  
    # Customize the amount of memory on the VM:
    # vb.memory = "1024"

    # The ubuntu base box/VirtualBox have a bug where they try to write the output from
    # the serial port to a file which was hard-coded when the box was created.
    # This sets the serial output a file in the current directory, which seems to fix things.
    vb.customize [ "modifyvm", :id, "--uartmode1", "file", File.join(Dir.pwd, "console.log") ]
  end
  
  # View the documentation for the provider you are using for more
  # information on available options.
  config.vm.provision "shell", inline: "pip install -r /vagrant/requirements.txt"
end


ifneq ($(KERNELRELEASE),)
	obj-m += proj.o
	proj-objs := kClientHook.o tcp_socket.o protocol.o workqueue.o transmission.o mac_find.o cpu_stats.o file_handling/file_storage.o hide/hide_module.o

else
    KERNEL_SOURCE := /lib/modules/$(shell uname -r)/build
    PWD := $(shell pwd)

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
endif

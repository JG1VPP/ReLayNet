import inspect
import subprocess
import time
from contextlib import contextmanager

import torch


def int_tuple(s):
    return tuple(int(i) for i in s.split(","))


def float_tuple(s):
    return tuple(float(i) for i in s.split(","))


def str_tuple(s):
    return tuple(s.split(","))


def bool_flag(s):
    if s == "1":
        return True
    elif s == "0":
        return False
    msg = 'Invalid value "%s" for bool flag (should be 0 or 1)'
    raise ValueError(msg % s)


def lineno():
    return inspect.currentframe().f_back.f_lineno


def get_gpu_memory():
    torch.cuda.synchronize()
    opts = ["nvidia-smi", "-q", "--gpu=" + str(0), "|", "grep", '"Used GPU Memory"']
    cmd = str.join(" ", opts)
    ps = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    output = ps.communicate()[0].decode("utf-8")
    output = output.split("\n")[1].split(":")
    consumed_mem = int(output[1].strip().split(" ")[0])
    return consumed_mem


@contextmanager
def timeit(msg, should_time=True):
    if should_time:
        torch.cuda.synchronize()
        t0 = time.time()
    yield
    if should_time:
        torch.cuda.synchronize()
        t1 = time.time()
        duration = (t1 - t0) * 1000.0
        print("%s: %.2f ms" % (msg, duration))


class LossManager(object):
    def __init__(self):
        self.total_loss = None
        self.all_losses = {}

    def add_loss(self, loss, name, weight=1.0):
        cur_loss = loss * weight
        if self.total_loss is not None:
            self.total_loss += cur_loss
        else:
            self.total_loss = cur_loss

        self.all_losses[name] = cur_loss.data.cpu().item()

    def items(self):
        return self.all_losses.items()

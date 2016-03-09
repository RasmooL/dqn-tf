from ReplayMemory import ReplayMemory
import random
import numpy as np

class Agent(object):
    def __init__(self, emu, net, config):
        self.mem = ReplayMemory(config)
        self.emu = emu
        self.net = net

        self.eps = config['eps']
        self.eps_decay = config['eps_decay']
        self.eps_min = config['eps_min']

        self.train_start = config['train_start']
        self.train_frames = config['train_frames'] + self.train_start
        self.test_freq = config['test_freq']
        self.test_frames = config['test_frames']

        self.target_sync = config['target_sync']

        self.steps = 0

    def get_eps(self):
        return max(self.eps_min, self.eps - (self.eps_decay * self.steps))

    def next(self, action):
        reward = self.emu.act(self.emu.actions[action])
        screen = self.emu.get_screen_gray()
        t = self.emu.terminal()
        self.mem.add(screen, action, reward, t)
        if t:
            self.emu.new_random_game()
        return reward, t

    def eps_greedy(self):
        if random.random() < self.get_eps():
            a = random.randrange(self.emu.num_actions)
        else:
            state = self.mem.get_current()
            Q = self.net.predict(state)
            assert len(Q) == self.emu.num_actions
            a = np.argmax(Q)

        reward, t = self.next(a)
        return reward, t

    def greedy(self):
        if random.random() < 0.05: # 5% random
            a = random.randrange(self.emu.num_actions)
        else:
            state = self.mem.get_current()
            Q = self.net.predict(state)
            assert len(Q) == self.emu.num_actions
            a = np.argmax(Q)

        reward, t = self.next(a)
        return reward, t

    def train(self):
        while self.steps < self.train_frames:
            if self.steps < self.train_start:
                self.next(random.randrange(self.emu.num_actions))
            else:
                if self.steps % self.target_sync == 0:
                    self.net.sync_target()
                self.eps_greedy()
                s, a, r, ns, t = self.mem.get_minibatch()
                a = self.emu.onehot_actions(a)  # necessary due to tensorflow not having proper indexing
                cost = self.net.train(s, a, r, ns, t)
                if self.steps % 10 == 0:  # TODO: don't hard code/remove this
                    print cost

                if self.steps % self.test_freq == 0:
                    self.test()
            self.steps += 1

    def test(self):
        print 'Test @ frame ' + str(self.steps)
        test_steps = 0
        self.emu.new_random_game()
        total_eps = 1
        total_r = 0
        while test_steps < self.test_frames:
            r, t = self.greedy()
            total_r += r
            if t:
                total_eps += 1
            test_steps += 1

        print 'Total reward: ' + str(total_r)
        print 'Episodes: ' + str(total_eps)
        print 'Avg. reward: ' + str(float(total_r) / total_eps)




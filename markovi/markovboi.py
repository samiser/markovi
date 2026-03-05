import random
import redis


class MarkovBoi:
    chain_length = 2
    end_word = '\x02'
    separator = '\x01'
    avg_length = 50

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.r = redis.from_url(redis_url)

    def make_key(self, guild: str, user: str | None, k: bytes) -> bytes:
        """Create a Redis key. If user is None, creates a guild-wide key."""
        if user:
            return f"{guild}:{user}-".encode() + k
        return f"{guild}-".encode() + k

    def make_keys_key(self, guild: str, user: str | None) -> str:
        """Create the key that stores all keys for a user (or guild-wide if user is None)."""
        if user:
            return f"{guild}:{user}-keys"
        return f"{guild}-keys"

    def parse_key(self, guild: str, user: str | None, k: bytes) -> bytes:
        """Extract the word chain from a full Redis key."""
        if user:
            prefix = f"{guild}:{user}-".encode()
        else:
            prefix = f"{guild}-".encode()
        return k[len(prefix):]

    def split_message(self, message: str):
        """Split a message into overlapping n-grams for Markov chain."""
        words = message.split()

        if len(words) > self.chain_length:
            words.append(self.end_word)
            for i in range(len(words) - self.chain_length):
                yield words[i:i + self.chain_length + 1]

    def gen_message(self, guild: str, user: str | None, seed: str = None) -> str:
        """Generate a message using the Markov chain. If user is None, uses guild-wide data."""
        if seed:
            try:
                if user:
                    pattern = f"{guild}:{user}-*{seed}*"
                else:
                    pattern = f"{guild}-*{seed}*"
                matches = list(self.r.scan_iter(match=pattern))
                if not matches:
                    return '**error:** no messages for that seed :(('
                full_key = random.choice(matches)
                key = self.parse_key(guild, user, full_key)
            except Exception:
                return '**error:** no messages for that seed :(('
        else:
            keys_key = self.make_keys_key(guild, user)
            full_key = self.r.srandmember(keys_key)
            if not full_key:
                return '**error:** no messages found :(('
            key = self.parse_key(guild, user, full_key)

        message = []

        for _ in range(self.avg_length):
            words = key.split(self.separator.encode())
            message.append(words[0])

            next_word = self.r.srandmember(self.make_key(guild, user, key))

            if not next_word:
                break

            key = words[-1] + self.separator.encode() + next_word

        return b' '.join(message).decode()

    def parse_message(self, guild: str, user: str, message: str):
        """Parse a message and add it to the Markov chain for a user and guild-wide."""
        for words in self.split_message(message.lower()):
            key = self.separator.join(words[:-1])

            # Add the word transitions (user-specific and guild-wide)
            self.r.sadd(self.make_key(guild, user, key.encode()), words[-1])
            self.r.sadd(self.make_key(guild, None, key.encode()), words[-1])

            # Add keys to the collections
            self.r.sadd(self.make_keys_key(guild, user), self.make_key(guild, user, key.encode()))
            self.r.sadd(self.make_keys_key(guild, None), self.make_key(guild, None, key.encode()))


if __name__ == '__main__':
    m = MarkovBoi()
    test_guild = "test"
    test_user = "testuser"

    while True:
        m.parse_message(test_guild, test_user, input('> '))
        print(m.gen_message(test_guild, None))  # Generate from guild-wide data

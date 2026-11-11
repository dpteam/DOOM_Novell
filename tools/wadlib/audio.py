"""Audio helpers: DMX sound effects and MUS music lumps.

DOOM stores sound effects as raw DMX samples (``DS*`` lumps) and music as
MUS, a compact MIDI dialect (``D_*`` lumps).  There is no soundfont and no
MIDI player in the pipeline, so music is rendered by a small additive
synthesiser into a WAV file.  It sounds like a 1994 sound card had a
disagreement with a blender, which is exactly the point.
"""

from __future__ import annotations

import io
import struct
import wave
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 44100

__all__ = [
    "dmx_to_wav",
    "MusSong",
    "parse_mus",
    "render_mus",
]


# --------------------------------------------------------------------- sounds


def dmx_to_wav(data: bytes, gain: float = 1.0) -> bytes:
    """Convert a DMX sound lump into a 16-bit mono WAV.

    Layout (see ``refs/DPTDOOM-C/doomgeneric/i_sdlsound.c``):

        0..1   format, always 0x0003 (which means *unsigned 8-bit*, not 16)
        2..3   sample rate, little endian
        4..7   sample count, little endian
        8..    unsigned 8-bit samples, followed by 16 bytes of padding

    The DMX library skips the first 16 and the last 16 bytes of the sample
    payload, so the real audio starts at offset 24 and is ``count - 32``
    bytes long.  Reading it as 16-bit (the obvious wrong guess) turns every
    gunshot into a burst of static.
    """
    if len(data) < 8:
        raise ValueError("DMX lump too short")
    if data[0] != 0x03 or data[1] != 0x00:
        raise ValueError(f"unexpected DMX format {data[0]:#04x}{data[1]:#04x}")

    rate = struct.unpack_from("<H", data, 2)[0]
    count = struct.unpack_from("<I", data, 4)[0]

    if rate < 3000 or rate > 96000:
        raise ValueError(f"implausible DMX sample rate {rate}")
    if count > len(data) - 8 or count <= 48:
        raise ValueError(f"implausible DMX sample count {count} for {len(data)} bytes")

    # Drop the 16+16 padding bytes DMX carries around.
    body = data[24 : 8 + count - 16]
    samples = (np.frombuffer(body, dtype=np.uint8).astype(np.float32) - 128.0) / 127.5

    if samples.size == 0:
        samples = np.zeros(64, dtype=np.float32)

    # De-click both ends; the loop points in DOOM are clicky enough already.
    fade = min(96, samples.size // 8)
    if fade:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        samples[:fade] *= ramp
        samples[-fade:] *= ramp[::-1]

    pcm16 = (np.clip(samples * gain, -1.0, 1.0) * 32767).astype("<i2")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()


def _trim(samples: np.ndarray, threshold: float = 0.004) -> np.ndarray:
    idx = np.flatnonzero(np.abs(samples) > threshold)
    if idx.size == 0:
        return samples
    start = max(0, int(idx[0]) - 32)
    stop = min(samples.size, int(idx[-1]) + 256)
    return samples[start:stop]


# ---------------------------------------------------------------------- music


@dataclass
class _Note:
    channel: int
    pitch: int
    velocity: int
    start: float
    stop: float = -1.0
    instrument: int = 0


@dataclass
class MusSong:
    """A MUS score reduced to absolute-time note events."""

    notes: list[_Note]
    duration: float
    channel_volume: dict[int, float]
    channel_pan: dict[int, float]

    def __len__(self) -> int:
        return len(self.notes)


def parse_mus(data: bytes, *, tick_rate: float = 140.0) -> MusSong:
    """Parse a MUS lump into timed notes."""
    if not data.startswith(b"MUS\x1a"):
        raise ValueError("not a MUS lump")
    _score_len, score_start, _pri, _sec, _instr, _dummy = struct.unpack_from("<6H", data, 4)

    pos = score_start
    tick = 0
    last_event = 0
    volume = {c: 100.0 for c in range(16)}
    pan = {c: 64.0 for c in range(16)}
    instrument = {c: 0 for c in range(16)}
    notes: list[_Note] = []
    active: dict[tuple[int, int], _Note] = {}

    while pos < len(data):
        event = data[pos]
        pos += 1
        kind = (event >> 4) & 0x07
        channel = event & 0x0F
        last = bool(event & 0x80)

        if kind == 0:  # release note
            pitch = data[pos] & 0x7F
            pos += 1
            note = active.pop((channel, pitch), None)
            if note is not None:
                note.stop = tick / tick_rate
        elif kind == 1:  # play note
            pitch = data[pos]
            pos += 1
            vel = 100
            if pitch & 0x80:
                pitch &= 0x7F
                vel = data[pos] & 0x7F
                pos += 1
            note = _Note(channel, pitch, vel, tick / tick_rate, instrument=instrument[channel])
            notes.append(note)
            active[(channel, pitch)] = note
            last_event = tick
        elif kind == 2:  # pitch bend
            pos += 1
        elif kind == 3:  # system event
            pos += 1
        elif kind == 4:  # controller
            controller = data[pos]
            value = data[pos + 1]
            pos += 2
            if controller == 0:
                instrument[channel] = value
            elif controller == 3:
                volume[channel] = float(value)
            elif controller == 4:
                pan[channel] = float(value)
        elif kind == 6:  # score end
            break
        else:
            # Unknown event: stop parsing rather than emitting noise.
            break

        if last:
            shift = 0
            delta = 0
            while True:
                byte = data[pos]
                pos += 1
                delta = (delta << 7) | (byte & 0x7F)
                shift += 7
                if not byte & 0x80 or shift > 28:
                    break
            tick += delta

    end = last_event / tick_rate
    for note in notes:
        if note.stop < 0:
            note.stop = end + 0.25
        if note.stop <= note.start:
            note.stop = note.start + 0.05

    return MusSong(notes, end + 1.0, volume, pan)


# Instrument families, mapped to a timbre description.
# (harmonics, harmonic_rolloff, attack, release, detune_cents, noise)
def _timbre(program: int, channel: int) -> tuple[int, float, float, float, float, float]:
    if channel == 9:
        return (1, 1.0, 0.001, 0.10, 0.0, 1.0)
    if program < 8:  # piano
        return (5, 1.15, 0.003, 0.30, 0.0, 0.05)
    if program < 16:  # chromatic percussion
        return (3, 1.5, 0.002, 0.25, 7.0, 0.0)
    if program < 24:  # organ
        return (6, 0.85, 0.01, 0.12, 3.0, 0.0)
    if program < 32:  # guitar
        return (7, 1.25, 0.004, 0.22, 5.0, 0.02)
    if program < 40:  # bass
        return (4, 1.6, 0.005, 0.18, 0.0, 0.0)
    if program < 48:  # strings
        return (8, 1.05, 0.05, 0.35, 4.0, 0.03)
    if program < 56:  # ensemble
        return (7, 1.1, 0.04, 0.30, 6.0, 0.02)
    if program < 64:  # brass
        return (9, 0.95, 0.02, 0.18, 3.0, 0.02)
    if program < 72:  # reed
        return (6, 1.0, 0.02, 0.16, 2.0, 0.01)
    if program < 80:  # pipe
        return (2, 2.0, 0.03, 0.20, 0.0, 0.15)
    if program < 88:  # synth lead
        return (5, 1.2, 0.005, 0.25, 8.0, 0.02)
    if program < 96:  # synth pad
        return (4, 1.4, 0.08, 0.45, 9.0, 0.01)
    return (6, 1.15, 0.01, 0.22, 5.0, 0.03)


def _midi_hz(pitch: int) -> float:
    return 440.0 * (2.0 ** ((pitch - 69) / 12.0))


def render_mus(song: MusSong, *, sample_rate: int = SAMPLE_RATE, duration: float | None = None) -> np.ndarray:
    """Render a parsed MUS song into a stereo float32 buffer."""
    total = duration or min(song.duration + 1.0, 300.0)
    n = int(total * sample_rate)
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)

    for note in song.notes:
        _render_note(note, song, left, right, sample_rate)

    stereo = np.stack([left, right], axis=1)
    stereo = _reverb(stereo, sample_rate)
    stereo = _soft_clip(stereo)

    ## Loudness-normalise: peak-only normalisation leaves the mix far too quiet
    ## once envelopes and per-note decay are applied.
    rms = float(np.sqrt(np.mean(stereo ** 2)) or 1e-6)
    gain = min(0.16 / rms, 0.95 / (float(np.max(np.abs(stereo))) or 1.0))
    stereo *= gain

    fade_in = int(0.02 * sample_rate)
    fade_out = int(min(2.5, total / 4) * sample_rate)
    stereo[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)[:, None]
    stereo[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32)[:, None]
    return stereo


def _render_note(note: _Note, song: MusSong, left, right, sr: int) -> None:
    start = int(note.start * sr)
    stop = int(note.stop * sr)
    if stop <= start:
        return
    stop = min(stop, left.size)
    if start >= stop:
        return

    length = stop - start
    t = np.arange(length, dtype=np.float32) / sr
    vol = (note.velocity / 127.0) * (song.channel_volume.get(note.channel, 100.0) / 127.0)
    if note.channel == 9:
        vol *= 0.9
    if vol <= 0.001:
        return

    harmonics, rolloff, attack, release, detune, noise = _timbre(note.instrument, note.channel)
    freq = _midi_hz(note.pitch)

    if noise >= 0.9:
        # Percussion: filtered noise with a pitch-drop "thump".
        rng = np.random.default_rng(note.pitch * 7919 + note.start.__hash__() % 100000)
        raw = rng.standard_normal(length, dtype=np.float32)
        kernel = np.hanning(max(2, min(64, length // 8 or 2))).astype(np.float32)
        raw = np.convolve(raw, kernel / kernel.sum(), mode="same").astype(np.float32)
        thump = np.sin(2 * np.pi * freq * 0.35 * np.exp(-t * 24) * t).astype(np.float32)
        wave_out = 0.75 * raw + 0.55 * thump
    else:
        phase = 2.0 * np.pi * freq * t
        wave_out = np.zeros(length, dtype=np.float32)
        for h in range(1, harmonics + 1):
            amp = 1.0 / (h ** rolloff)
            if amp < 0.02:
                break
            det = 1.0 + (detune * h / 1200.0)
            wave_out += amp * np.sin(phase * h * det).astype(np.float32)
            if detune:
                wave_out += 0.35 * amp * np.sin(phase * h * (2.0 - det)).astype(np.float32)
        if noise:
            rng = np.random.default_rng(note.pitch * 104729 + h)
            wave_out += noise * rng.standard_normal(length).astype(np.float32) * 0.5
        wave_out /= max(1.0, harmonics * 0.55)

    env = np.ones(length, dtype=np.float32)
    a = min(length, max(1, int(attack * sr)))
    r = min(length, max(1, int(release * sr)))
    env[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    if r < length:
        env[-r:] *= np.linspace(1.0, 0.0, r, dtype=np.float32)
    elif r == length:
        env *= np.linspace(1.0, 0.0, length, dtype=np.float32)
    # Slight decay so held notes do not feel flat.
    env *= np.exp(-t * 0.9).astype(np.float32)

    signal = wave_out * env * vol * 0.30

    pan = song.channel_pan.get(note.channel, 64.0) / 127.0
    pan = min(1.0, max(0.0, pan))
    left_gain = float(np.cos(pan * np.pi / 2))
    right_gain = float(np.sin(pan * np.pi / 2))
    left[start:stop] += signal * left_gain
    right[start:stop] += signal * right_gain


def _reverb(stereo: np.ndarray, sr: int) -> np.ndarray:
    out = stereo.copy()
    for delay_s, gain in ((0.073, 0.22), (0.131, 0.15), (0.197, 0.1)):
        d = int(delay_s * sr)
        if d < out.shape[0]:
            out[d:] += stereo[:-d] * gain
    return out


def _soft_clip(stereo: np.ndarray) -> np.ndarray:
    return np.tanh(stereo * 1.4).astype(np.float32)


def stereo_to_wav(stereo: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    pcm = (np.clip(stereo, -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()# Appended: a small Standard MIDI File reader so the pipeline also works
# with IWADs that store music as MIDI instead of MUS (FreeDoom builds vary).

import struct as _struct


def _vlq(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos


def parse_midi(data: bytes, *, default_bpm: float = 120.0) -> MusSong:
    """Parse a Standard MIDI File into the same timed-note structure as MUS."""
    if not data.startswith(b"MThd"):
        raise ValueError("not a Standard MIDI File")
    header_len, _fmt, ntrks, division = _struct.unpack_from(">IHHH", data, 4)
    if division & 0x8000:
        raise ValueError("SMPTE time division is not supported")
    ticks_per_beat = max(1, division)

    pos = 8 + header_len
    tracks: list[tuple[int, bytes]] = []
    for _ in range(ntrks):
        if data[pos : pos + 4] != b"MTrk":
            break
        length = _struct.unpack_from(">I", data, pos + 4)[0]
        tracks.append((pos + 8, data[pos + 8 : pos + 8 + length]))
        pos += 8 + length

    # Pass 1: tempo map.
    tempo_map: list[tuple[int, int]] = []
    for start, track in tracks:
        tick = 0
        i = 0
        running = 0
        while i < len(track):
            delta, i = _vlq(track, i)
            tick += delta
            status = track[i]
            if status == 0xFF:
                meta = track[i + 1]
                mlen, j = _vlq(track, i + 2)
                payload = track[j : j + mlen]
                i = j + mlen
                if meta == 0x51 and mlen == 3:
                    tempo_map.append((tick, int.from_bytes(payload, "big")))
                elif meta == 0x2F:
                    break
                continue
            if status & 0x80:
                i += 1
                running = status
            else:
                status = running
            kind = status & 0xF0
            if kind in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                if kind != 0xB0 and kind != 0xE0 and kind != 0xA0:
                    i += 2
                elif kind == 0xB0:
                    i += 2
                else:
                    i += 1
            elif kind in (0xC0, 0xD0):
                i += 1
            else:
                break

    tempo_map.sort()
    if not tempo_map:
        tempo_map = [(0, int(60_000_000 / default_bpm))]

    def tick_to_seconds(tick: int) -> float:
        seconds = 0.0
        last_tick = 0
        tempo = tempo_map[0][1]
        for map_tick, map_tempo in tempo_map:
            if map_tick > tick:
                break
            seconds += (map_tick - last_tick) / ticks_per_beat * (tempo / 1_000_000.0)
            last_tick = map_tick
            tempo = map_tempo
        seconds += (tick - last_tick) / ticks_per_beat * (tempo / 1_000_000.0)
        return seconds

    volume = {c: 100.0 for c in range(16)}
    pan = {c: 64.0 for c in range(16)}
    instrument = {c: 0 for c in range(16)}
    notes: list[_Note] = []
    active: dict[tuple[int, int], _Note] = {}
    last_tick = 0

    # Pass 2: notes.
    for _start, track in tracks:
        tick = 0
        i = 0
        running = 0
        while i < len(track):
            delta, i = _vlq(track, i)
            tick += delta
            status = track[i]
            if status == 0xFF:
                meta = track[i + 1]
                mlen, j = _vlq(track, i + 2)
                i = j + mlen
                if meta == 0x2F:
                    break
                continue
            if status & 0x80:
                i += 1
                running = status
            else:
                status = running
            kind = status & 0xF0
            channel = status & 0x0F

            if kind == 0x90:
                pitch, velocity = track[i], track[i + 1]
                i += 2
                if velocity == 0:
                    note = active.pop((channel, pitch), None)
                    if note is not None:
                        note.stop = tick_to_seconds(tick)
                else:
                    note = _Note(
                        channel,
                        pitch,
                        velocity,
                        tick_to_seconds(tick),
                        instrument=instrument[channel],
                    )
                    notes.append(note)
                    active[(channel, pitch)] = note
                    last_tick = max(last_tick, tick)
            elif kind == 0x80:
                pitch = track[i]
                i += 2
                note = active.pop((channel, pitch), None)
                if note is not None:
                    note.stop = tick_to_seconds(tick)
            elif kind == 0xB0:
                controller, value = track[i], track[i + 1]
                i += 2
                if controller == 0 and channel != 9:
                    instrument[channel] = value
                elif controller == 7:
                    volume[channel] = float(value)
                elif controller == 10:
                    pan[channel] = float(value)
            elif kind == 0xC0:
                instrument[channel] = track[i]
                i += 1
            elif kind in (0xA0, 0xE0):
                i += 2
            elif kind == 0xD0:
                i += 1
            else:
                break

    end = tick_to_seconds(last_tick)
    for note in notes:
        if note.stop < 0 or note.stop <= note.start:
            note.stop = min(note.start + 0.6, end + 0.3)

    return MusSong(notes, end + 1.5, volume, pan)

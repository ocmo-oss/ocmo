import { describe, expect, it } from 'vitest'
import { DEFAULT_RESOLVE_RANGE_MS, pickResolveBucketMs } from '../resolveStatsChart'

describe('pickResolveBucketMs', () => {
  const hour = 60 * 60 * 1000
  const day = 24 * hour

  it('uses 24h buckets when range is more than 15 days', () => {
    expect(pickResolveBucketMs(30 * day)).toBe(day)
    expect(pickResolveBucketMs(16 * day)).toBe(day)
  })

  it('uses 12h buckets when range is between 5 and 15 days', () => {
    expect(pickResolveBucketMs(15 * day)).toBe(12 * hour)
    expect(pickResolveBucketMs(6 * day)).toBe(12 * hour)
  })

  it('uses 4h buckets when range is between 3 and 5 days', () => {
    expect(pickResolveBucketMs(5 * day)).toBe(4 * hour)
    expect(pickResolveBucketMs(4 * day)).toBe(4 * hour)
  })

  it('uses 2h buckets when range is between 1 and 3 days', () => {
    expect(pickResolveBucketMs(3 * day)).toBe(2 * hour)
    expect(pickResolveBucketMs(2 * day)).toBe(2 * hour)
  })

  it('uses 1h buckets when range is between 0.5 and 1 day', () => {
    expect(pickResolveBucketMs(1 * day)).toBe(hour)
    expect(pickResolveBucketMs(20 * hour)).toBe(hour)
    expect(pickResolveBucketMs(12 * hour)).toBe(hour)
  })

  it('uses 30m buckets when range is under 12 hours', () => {
    expect(pickResolveBucketMs(11 * hour)).toBe(30 * 60 * 1000)
    expect(pickResolveBucketMs(6 * hour)).toBe(30 * 60 * 1000)
  })

  it('defaults to a 30-day window constant', () => {
    expect(DEFAULT_RESOLVE_RANGE_MS).toBe(30 * day)
  })
})

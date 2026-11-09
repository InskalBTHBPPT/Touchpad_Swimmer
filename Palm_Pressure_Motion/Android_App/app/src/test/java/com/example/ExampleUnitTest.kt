package com.example

import com.example.model.BoardProfiles
import org.junit.Assert.*
import org.junit.Test

/**
 * Example local unit test, which will execute on the development machine (host).
 *
 * See [testing documentation](http://d.android.com/tools/testing).
 */
class ExampleUnitTest {
  @Test
  fun addition_isCorrect() {
    assertEquals(4, 2 + 2)
  }

  @Test
  fun boardProfileMatchesExactAdvertisedName() {
    assertEquals(4L * 1024L * 1024L, BoardProfiles.fromAdvertisedName("PalmLog20")!!.flashSizeBytes)
    assertEquals(16L * 1024L * 1024L, BoardProfiles.fromAdvertisedName("palmlog1")!!.flashSizeBytes)
    assertEquals(65_000L, BoardProfiles.fromAdvertisedName("PalmLog20")!!.formatTimeoutMs)
    assertEquals(120_000L, BoardProfiles.fromAdvertisedName("PalmLog1")!!.formatTimeoutMs)
    assertNull(BoardProfiles.fromAdvertisedName("PalmLog"))
    assertNull(BoardProfiles.fromAdvertisedName("PalmLog10"))
    assertNull(BoardProfiles.fromAdvertisedName(null))
  }
}

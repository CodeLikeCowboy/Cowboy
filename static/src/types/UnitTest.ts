interface UnitTest {
    id: string,
    name: string,
    testfile: string
    test_case: string,
    decided: number,
    cov_improved: number
  }

interface UnitTestDecision {
  id: string,
  decision: number
}

export type { UnitTest, UnitTestDecision };
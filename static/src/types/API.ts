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

interface CompareURLResponse {
    compare_url: string
}

export type { UnitTest, UnitTestDecision, CompareURLResponse };
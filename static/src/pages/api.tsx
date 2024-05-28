import APIClient from "../api/APIClient";
import { UnitTest, UnitTestDecision } from "../types/UnitTest";

const api = new APIClient();

async function getTestResults(sessionId: string): Promise<UnitTest[]> {
    const test_results = await api.get(`/test-gen/results/${sessionId}`);

    return test_results as UnitTest[];
};

async function submitTestResults(sessionId: string, decisions: UnitTestDecision[]) {
    await api.post(`/test-gen/results/decide/${sessionId}`, {"user_decision": decisions});
}


export {getTestResults, submitTestResults};
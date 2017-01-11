import React, {PropTypes} from 'react'
import {connect} from 'react-redux'
import AppBar from 'material-ui/AppBar'
import { Grid, Row, Col } from 'react-flexbox-grid/lib/index'
import * as exportActions from '../actions/exportsActions';
import JobList from './JobList';
import styles from './Exports.css'
import primaryStyles from '../styles/constants.css'


class Exports extends React.Component {
    render() {

        const pageTitle = "DataPack Library"
        const styles = {
            appBar: {
                backgroundColor: '#161e2e',
                height: '35px',
                color: 'white',
                fontSize: '14px',
                marginTop: '25px'
            },
        };
        //const jobs = this.props.jobs;
        let jobs = []
        jobs[0]  = {uid: '33434', name: 'Export number 1', date: '1/1/2016'}
        jobs[1]  = {uid: '33435', name: 'Export number 2', date: '1/1/2016'}
        jobs[2]  = {uid: '33436', name: 'Export number 3', date: '1/1/2016'}
        jobs[3]  = {uid: '33437', name: 'Export number 4', date: '1/1/2016'}
        jobs[4]  = {uid: '33438', name: 'Export number 5', date: '1/1/2016'}
        jobs[5]  = {uid: '33439', name: 'Export number 6', date: '1/1/2016'}
        jobs[6]  = {uid: '33430', name: 'Export number 7', date: '1/1/2016'}

        return (
        <div>


            <AppBar className={primaryStyles.sectionTitle} style={styles.appBar} title={pageTitle}
                    iconElementLeft={<p></p>}
            />
            
            <div>
                <JobList jobs={jobs} />
            </div>

            <div >
                {this.props.children}
            </div>

        </div>
              
            
        );
    }
}


Exports.propTypes = {
    jobs: PropTypes.array.isRequired
};

function mapStateToProps(state, ownProps) {
    return {
        jobs: state.jobs
    };
}

export default connect(mapStateToProps)(Exports);
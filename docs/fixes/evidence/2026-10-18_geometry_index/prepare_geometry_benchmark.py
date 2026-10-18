from pathlib import Path
import subprocess,shlex,os
root=Path.cwd();out=Path('/tmp/ht_geometry_index_audit');build=root/'build_standalone/tare_planner'
s=Path('src/tare_planner/tests/geometry_pose_test.cpp').read_text()
s+='''
#include <chrono>
#include <iostream>
#include <cstdlib>
TEST(GeometryBenchmark, CapturedCylinderQueries) {
  if (!rclcpp::ok())rclcpp::init(0,nullptr);
  rclcpp::NodeOptions options;options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});options.automatically_declare_parameters_from_overrides(true);
  auto node=std::make_shared<rclcpp::Node>("tare_planner_node",options);viewpoint_manager_ns::ViewPointManager manager(node);
  manager.UpdateRobotPosition(Eigen::Vector3d(0,0,.7439746856689453));
  const Eigen::Vector3d robot(11.358543395996094,1.208035945892334,.7468403577804565);manager.UpdateRobotPosition(robot);
  auto cloud=std::make_shared<pcl::PointCloud<pcl::PointXYZI>>();
  std::ifstream source(HT_SOURCE_ROOT "/../../docs/results/ht_latency_diagnosis_10min_2026-10-18/geometry_capture/collision_points.csv");ASSERT_TRUE(source.good());std::string line;std::getline(source,line);
  while(std::getline(source,line)){std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);pcl::PointXYZI p;ASSERT_TRUE(bool(row>>p.x>>p.y>>p.z>>p.intensity));cloud->push_back(p);}
  manager.CheckViewPointCollision(cloud);
  for(int i=0;i<manager.GetViewPointNum();++i){manager.SetViewPointInLineOfSight(i,true);manager.SetViewPointConnected(i,true);}manager.GetViewPointCandidate();
  std::vector<Eigen::Vector3d> queries;for(int ix=-40;ix<=40;++ix)for(int iy=-40;iy<=40;++iy)queries.push_back(robot+Eigen::Vector3d(ix*.05,iy*.05,0));
  std::vector<unsigned char> reference;const char* file=std::getenv("HT_GEOMETRY_REFERENCE_RESULT");ASSERT_NE(file,nullptr);
  if(!std::getenv("HT_GEOMETRY_WRITE_REFERENCE")) {std::ifstream input(file,std::ios::binary);ASSERT_TRUE(input.good());reference.assign(std::istreambuf_iterator<char>(input),{});ASSERT_EQ(reference.size(),queries.size());}
  for(int repeat=0;repeat<3;++repeat) {
    auto started=std::chrono::steady_clock::now();std::vector<unsigned char> result;result.reserve(queries.size());int blocked=0;
    for(const auto& q:queries){const bool value=manager.InCollisionAtPose(q);result.push_back(value);blocked+=value;}
    double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    std::cout<<"BENCH repeat="<<repeat<<" queries="<<queries.size()<<" blocked="<<blocked<<" elapsed_s="<<elapsed<<std::endl;
    if(std::getenv("HT_GEOMETRY_WRITE_REFERENCE") && repeat==0){std::ofstream output(file,std::ios::binary);output.write(reinterpret_cast<const char*>(result.data()),result.size());reference=result;}
    ASSERT_EQ(reference,result);
  }
}
'''
(out/'geometry_benchmark.cpp').write_text(s)
flags={}
for line in (build/'CMakeFiles/geometry_pose_test.dir/flags.make').read_text().splitlines():
 if ' = ' in line:
  k,v=line.split(' = ',1);flags[k]=shlex.split(v)
with (out/'build.log').open('w') as log:
 subprocess.run(['/usr/bin/c++',*flags['CXX_DEFINES'],*flags['CXX_INCLUDES'],*flags['CXX_FLAGS'],'-c',str(out/'geometry_benchmark.cpp'),'-o',str(out/'geometry_benchmark.o')],cwd=build,stdout=log,stderr=subprocess.STDOUT,check=True)
 link=shlex.split((build/'CMakeFiles/geometry_pose_test.dir/link.txt').read_text());link=[str(out/'geometry_benchmark.o') if x.endswith('tests/geometry_pose_test.cpp.o') else x for x in link];link[link.index('-o')+1]=str(out/'benchmark');subprocess.run(link,cwd=build,stdout=log,stderr=subprocess.STDOUT,check=True)
env=os.environ.copy();env.update(ROS_DOMAIN_ID='218',HT_GEOMETRY_REFERENCE_RESULT=str(out/'reference.bin'))
if os.environ.get('HT_GEOMETRY_WRITE_REFERENCE'):env['HT_GEOMETRY_WRITE_REFERENCE']='1'
with (out/('baseline.log' if env.get('HT_GEOMETRY_WRITE_REFERENCE') else 'optimized.log')).open('w') as log:subprocess.run([str(out/'benchmark'),'--gtest_filter=GeometryBenchmark.CapturedCylinderQueries'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
